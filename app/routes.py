from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, send_file, jsonify, make_response, abort
from sqlalchemy import func
from flask_login import login_user, logout_user, current_user, login_required
from .models import db, Users, Products, Members, Sale, saleDetails
from .roleRequired import role_required
from .forms import LoginForm
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, date
import uuid
import io
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from io import BytesIO


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Blueprint('main', __name__)

@app.route('/', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            session['user_id'] = user.id
            session['user_name'] = user.username
            session['role'] = user.role
            flash(f"Selamat datang, {user.username}!", "success")
            return redirect(url_for('main.dashboard'))
        else:
            flash('Username atau password salah', 'danger')
    return render_template('login.html', form=form)

# >>>>>>>>>>>>>>>>>>>>>>>>>> DASHBOARD API <<<<<<<<<<<<<<<<<<<<<<<<<< #

def hitung_total_penjualan_hari_ini():
    today = date.today()

    total = (
        Sale.query
        .filter(Sale.created_at == today)
        .count()
    )

    total_member = (
        Sale.query
        .filter(Sale.created_at == today, Sale.member_id.isnot(None))
        .count()
    )

    total_non_member = (
        Sale.query
        .filter(Sale.created_at == today, Sale.member_id.is_(None))
        .count()
    )

    return total, total_member, total_non_member


def get_data_dashboard_admin():
    today = date.today()
    start_date = today.replace(day=1)

    results = (
        db.session.query(Sale.created_at, func.count(Sale.id))
        .filter(Sale.created_at >= start_date)
        .group_by(Sale.created_at)
        .order_by(Sale.created_at)
        .all()
    )

    penjualan_harian = [(tgl.strftime('%d %b'), jumlah) for tgl, jumlah in results]
    penjualan_harian = penjualan_harian or []

    member_count = Sale.query.filter(Sale.member_id.isnot(None)).count() or 0
    non_member_count = Sale.query.filter(Sale.member_id.is_(None)).count() or 0

    product_query = (
        db.session.query(saleDetails.product_name, func.count(saleDetails.id))
        .group_by(saleDetails.product_name)
        .order_by(func.count(saleDetails.id).desc())
        .all()
    )

    product_labels = [p[0] for p in product_query]
    product_values = [p[1] for p in product_query]

    return penjualan_harian, member_count, non_member_count, start_date, today, product_labels, product_values


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        penjualan_harian, member_count, non_member_count, start_date, today, product_labels, product_values = get_data_dashboard_admin()

        return render_template(
            'dashboard/dashboard_admin.html',
            penjualan_harian=penjualan_harian,
            member_count=member_count,
            non_member_count=non_member_count,
            start_date=start_date,
            today=today,
            product_labels=product_labels,
            product_values=product_values
        )
    
    elif current_user.role == 'petugas':
        total_penjualan, member_count, non_member_count = hitung_total_penjualan_hari_ini()
        today = date.today()
        return render_template(
            'dashboard/dashboard_petugas.html',
            total_penjualan=total_penjualan,
            today=today,
            non_member_count=non_member_count,
            member_count=member_count,
        )
    
    else:
        flash("Role tidak dikenal", "danger")
        return redirect(url_for('login.html'))





@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Berhasil logout", "info")
    return redirect(url_for('main.login'))


# >>>>>>>>>>>>>>>>>>>>>>>>>>     PRODUK API     <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
@app.route('/products', methods=['GET'])
@login_required
def read_all_produk():
    all_products = Products.query.all()
    return render_template('product/product.html', products=all_products)

@app.route('/sales/<int:sale_id>/detail', methods=['GET'])
@login_required
def sale_detail(sale_id):
    sale_detail_items = saleDetails.query.filter_by(sale_id=sale_id).all()

    if not sale_detail_items:
        abort(404, description="Detail penjualan tidak ditemukan")

    sale = Sale.query.get_or_404(sale_id)

    return render_template('sale/sale_detail_modal.html', sale=sale, sale_detail_items=sale_detail_items)



@app.route('/products/tambah', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def tambah_produk():
    if request.method == 'POST':
        name = request.form['name']
        price =  request.form['price']
        stock = request.form['stock']
        image_file = request.files.get('image')

        if not name or not price or not stock:
            flash("Semua field wajib diisi")
            return redirect(url_for('tambah_produk'))
        
        
        try:
            price =  float(price.replace('.', '').replace(',', ''))
            stock = int(stock)
        except ValueError:
            flash("Format price atau stock tidak sesuai dengan yang diharapkan")
            return redirect(url_for('tambah_produk'))
        
        if image_file and image_file.filename != '':
            if '.' in image_file.filename and image_file.filename.rsplit('.', 1)[1].lower() in ['jpg', 'jpeg', 'png', 'gif']:
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
            else:
                flash("Ekstensi file tidak didukung", "danger")
                return redirect(url_for('produk.tambah_produk'))
        else:
            filename = None

        
        new_produk = Products(name=name, price=price, stock=stock, image=filename)
        db.session.add(new_produk)
        db.session.commit()
        flash("Products berhasil ditambahkan")
        return redirect(url_for('main.read_all_produk'))

    return render_template('product/tambah_produk.html')


@app.route('/product/delete/<int:product_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def delete_product(product_id):
    product = Products.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Berhasil menghapus product")
    return redirect(url_for('main.read_all_produk'))

@app.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_product(product_id):
    product = Products.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.price = request.form['price']
        product.stock = request.form['stock']
        image = request.files.get('image_file')

        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image = filename

        db.session.commit()
        flash('Produk berhasil diperbarui!', 'success')
        return redirect(url_for('main.read_all_produk'))

    return render_template('product/edit_product.html', product=product)


# >>>>>>>>>>>>>>>>>>>>>>> PENJUALAN API <<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #

@app.route('/sale', methods=['GET'])
@login_required
def get_all_sale():
    all_sale = Sale.query.all()
    print(all_sale)
    return render_template('sale/sale.html', sales=all_sale)


@app.route('/sale/create', methods=['GET', 'POST'])
@login_required
def create_sale():
    products = Products.query.all()
    if request.method == 'POST':
        items = []
        total_price = 0

        for product in products:
            qty = int(request.form.get(f'quantities[{product.id}]', 0))
            if qty > 0:
                if qty > product.stock:
                    flash(f"Stok produk {product.name} tidak mencukupi", "danger")
                    return redirect(url_for('main.create_sale'))

                subtotal = qty * product.price
                items.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'quantity': qty,
                    'price': product.price,
                    'subtotal': subtotal,
                    'image': product.image
                })
                total_price += subtotal

        if not items:
            flash("Pilih setidaknya satu produk.", "warning")
            return redirect(url_for('main.create_sale'))

        session['pending_sale'] = {
            'items': items,
            'total_price': total_price
        }
        return redirect(url_for('main.payment_step1'))

    return render_template('sale/create_sale.html', products=products)

@app.route('/sale/payment/step1', methods=['GET', 'POST'])
@login_required
def payment_step1():
    if 'pending_sale' not in session:
        return redirect(url_for('main.create_sale'))

    if request.method == 'POST':
        status = request.form['is_member']
        phone = request.form.get('phone_number')
        total_price = int(session['pending_sale']['total_price'])
        total_pay_str = request.form['total_pay'].replace('.', '')
        total_pay = float(total_pay_str)

        if total_pay < total_price:
            flash("Total bayar tidak boleh kurang dari total harga!", "danger")
            return redirect(url_for('main.payment_step1'))

        if status == 'member' and not phone:
            flash("Nomor HP wajib diisi untuk member", "warning")
            return redirect(url_for('main.payment_step1'))

        member = None
        is_first_transaction = False

        if status == 'member':
            member = Members.query.filter_by(phone_number=phone).first()
            if not member:
                member = Members(phone_number=phone, points=0)
                db.session.add(member)
                db.session.commit()
                flash("Member baru berhasil dibuat", "info")

            existing_sale = Sale.query.filter_by(member_id=member.id).first()
            is_first_transaction = existing_sale is None

            member.points += int(total_price * 0.1)
            db.session.commit()

            session['member_id'] = member.id

        session['payment'] = {
            'is_member': status,
            'phone_number': phone,
            'total_price': total_price,
            'total_pay': total_pay,
            'is_first_transaction': is_first_transaction
        }

        return redirect(url_for('main.payment_step2'))

    return render_template(
        'sale/payment_step1.html',
        items=session['pending_sale']['items'],
        total_price=session['pending_sale']['total_price'],
        total_pay=session.get('payment', {}).get('total_pay')
    )



@app.route('/sale/payment/step2', methods=['GET', 'POST'])
@login_required
def payment_step2():
    if 'payment' not in session:
        return redirect(url_for('main.payment_step1'))

    is_member = session['payment']['is_member']
    is_first_transaction = session['payment'].get('is_first_transaction', False)
    member = None
    

    if is_member == 'member':
        member = Members.query.get(session.get('member_id'))

    if request.method == 'POST':
        used_point = 0

        if is_member == 'member' and member:
            member_name = request.form.get('member_name')
            if member_name:
                member.name = member_name
                db.session.commit()

        if is_member == 'member' and 'use_point' in request.form:
            if is_first_transaction:
                flash("Poin tidak dapat digunakan pada transaksi pertama.", "warning")
                return redirect(url_for('main.payment_step2'))

            if member.points > 0:
                if member.points < session['pending_sale']['total_price']:
                    session['pending_sale']['total_price'] -= member.points
                    used_point = member.points
                    member.points = 0
                    db.session.commit()

        sale = Sale(
            member_id=member.id if member else None,
            total_price=session['pending_sale']['total_price'],
            member_status="member" if member else "Non-member",
            created_by=current_user.username,
            created_at=datetime.today() if member else None,
        )
        db.session.add(sale)
        db.session.flush()

        invoice_code = str(uuid.uuid4()).split('-')[0].upper()
        total_pay = session['payment'].get('total_pay', 0)
        total_price=session['pending_sale']['total_price']
        refund_amount = total_pay - total_price 


        for item in session['pending_sale']['items']:
            product = Products.query.get(item['product_id'])
            product.stock -= item['quantity']
            db.session.add(product)

            sale_detail = saleDetails(
                sale_id=sale.id,
                member_id=member.id if member else None,
                member_since=member.created_at if member else None,
                member_point=member.points if member else 0,
                invoice=invoice_code,
                product_name=item['product_name'],
                quantity=item['quantity'],
                product_price=item['price'],
                total_price=item['subtotal'],
                total_pay=total_pay,
                used_point=used_point / len(session['pending_sale']['items']) if used_point else 0,
                refund=refund_amount
            )
            db.session.add(sale_detail)

        db.session.commit()
        sale_details = saleDetails.query.filter_by(sale_id=sale.id).all()

        session.pop('payment', None)
        session.pop('pending_sale', None)
        session.pop('member_id', None)
        return render_template('sale/receipt.html',
                       member=member,
                       sale=sale,
                       sale_details=sale_details,
                       invoice=invoice_code,
                       used_point=used_point,
                       cashier=current_user.username,
                       change=refund_amount)

    return render_template('sale/payment_step2.html', member=member, steps=[
        "Isi data pelanggan",
        "Pilih metode pembayaran",
        "Selesaikan transaksi"
    ],
    is_first_transaction=is_first_transaction
    )



@app.route('/sale/export-excel', methods=['GET'])
@login_required
def export_sales_excel():
    sales = Sale.query.all()
    data = []

    for sale in sales:
        member = sale.member
        details = sale.sale_detail

        nama_pelanggan = member.name if member else "Non-member"
        no_hp = member.phone_number if member else "-"

        poin_pelanggan = details[0].member_point if details and details[0].member_point else 0

        produk_list = [
            f"{d.product_name} ({d.quantity}x: {int(d.product_price)})"
            for d in details
        ]
        produk_str = "\n".join(produk_list)

        total_harga = sum(d.total_price + d.used_point for d in details)
        total_bayar = sale.total_price
        total_diskon_point = sum(d.used_point for d in details)
        total_pembelian = total_bayar
        kembalian = sum(d.refund for d in details if d.refund)
        tanggal_pembelian = sale.created_at.strftime('%Y-%m-%d')

        data.append({
            "Nama Pelanggan": nama_pelanggan,
            "No HP Pelanggan": no_hp,
            "Poin Pelanggan": poin_pelanggan,
            "Produk": produk_str,
            "Total Harga": total_harga,
            "Total Bayar": total_bayar,
            "Total Diskon dari Point": total_diskon_point,
            "Total Pembelian": total_pembelian,
            "Kembalian": kembalian,
            "Tanggal Pembelian": tanggal_pembelian,
        })

    df = pd.DataFrame(data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Penjualan')

        workbook = writer.book
        worksheet = writer.sheets['Penjualan']

        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            column_len = max(df[value].astype(str).map(len).max(), len(value))
            worksheet.set_column(col_num, col_num, min(column_len + 2, 50), wrap_format)

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='data_penjualan.xlsx'
    )


@app.route('/sale/<int:sale_id>', methods=['GET'])
@login_required
def read_sale_by_id(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    details = sale.sale_detail
    member = sale.member

    nama_pelanggan = member.name if member else "Non-member"
    no_hp = member.phone_number if member else "-"
    poin_pelanggan = member.points if member else 0

    produk_list = []
    total_diskon_point = 0
    total_refund = 0
    total_dibayar = 0

    for d in details:
        produk_list.append({
            "invoice": d.invoice,
            "nama_produk": d.product_name,
            "jumlah": d.quantity,
            "harga": d.product_price,
            "subtotal": d.total_price
        })
        total_diskon_point += d.used_point or 0
        total_refund += d.refund or 0
        total_dibayar += d.total_pay or 0

    kembalian = total_dibayar - sale.total_price

    data = {
        "id": sale.id,
        "invoice": details[0].invoice if details else "-",
        "tanggal_pembelian": sale.created_at.strftime('%Y-%m-%d'),
        "nama_kasir": sale.created_by,
        "nama_pelanggan": nama_pelanggan,
        "no_hp_pelanggan": no_hp,
        "poin_pelanggan": poin_pelanggan,
        "produk": produk_list,
        "total_bayar": sale.total_price,
        "jumlah_dibayar": total_dibayar,
        "kembalian": kembalian,
        "poin_digunakan": total_diskon_point,
        "total_refund": total_refund,
    }

    return render_template('saleDetail/sale_detail.html', sale=data)

@app.route('/struk/<int:sale_id>')
@login_required
def generate_struk_pdf(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    member = sale.member
    sale_detail_items = sale.sale_detail

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    def draw_text(label, value):
        nonlocal y
        p.drawString(3 * cm, y, f"{label}: {value}")
        y -= 20

    p.setFont("Helvetica-Bold", 16)
    p.drawString(3 * cm, y, "Struk Transaksi")
    y -= 30

    p.setFont("Helvetica", 12)
    invoice = sale_detail_items[0].invoice if sale_detail_items else "-"
    draw_text("ID Transaksi", invoice)
    draw_text("Member Sejak", member.created_at.strftime('%d-%m-%Y') if member and member.created_at else "-")
    draw_text("Poin Tersisa", f"{member.points:.2f}" if member else "0")
    draw_text("Tanggal", sale.created_at.strftime('%d-%m-%Y'))
    draw_text("Nama Kasir", sale.created_by)

    y -= 10
    p.line(2.5 * cm, y, width - 2.5 * cm, y)
    y -= 30

    p.setFont("Helvetica-Bold", 12)
    p.drawString(3 * cm, y, "Nama Produk")
    p.drawString(9 * cm, y, "Qty")
    p.drawString(11 * cm, y, "Harga")
    p.drawString(14 * cm, y, "Subtotal")
    y -= 20

    p.setFont("Helvetica", 11)
    total_refund = 0
    total_used_point = 0
    for item in sale_detail_items:
        if y < 100:
            p.showPage()
            y = height - 50
        p.drawString(3 * cm, y, item.product_name)
        p.drawString(9 * cm, y, str(item.quantity))
        p.drawString(11 * cm, y, f"Rp {item.product_price:,.0f}")
        p.drawString(14 * cm, y, f"Rp {item.total_price:,.0f}")
        total_refund += item.refund or 0
        total_used_point += item.used_point or 0
        y -= 20

    # Tambahkan informasi point dan kembalian di bawah
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    draw_text("Total Point yang Digunakan", f"Rp {total_used_point:,.0f}")
    draw_text("Total Kembalian", f"Rp {total_refund:,.0f}")

    y -= 20
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(3 * cm, y, "Terima kasih telah berbelanja!")

    p.showPage()
    p.save()

    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=struk_{sale_id}.pdf'
    return response


# >>>>>>>>>>>>>>>>>>> USER API <<<<<<<<<<<<<<<<<<<<<  #

@app.route('/user', methods=['GET'])
@role_required('admin')
@login_required
def get_all_user():
    all_user = Users.query.all()
    print(all_user)
    return render_template('user/user.html', users=all_user)

@app.route('/user/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password) 
        user = Users(username=username, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()

        flash('User berhasil ditambahkan', 'success')
        return redirect(url_for('main.get_all_user'))

    return render_template('user/create_user.html')

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = Users.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.role = request.form['role']
        db.session.commit()
        flash('User berhasil diperbarui.')
        return redirect(url_for('main.get_all_user'))
    return render_template('user/edit_user.html', user=user)


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User berhasil dihapus.')
    return redirect(url_for('main.get_all_user'))





