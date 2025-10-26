from openpyxl import Workbook
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__)
app.secret_key = 'rahasia_login_admin'  # ganti dengan secret key yang aman
app = Flask(__name__)
import sqlite3


def koneksi():
    return sqlite3.connect('laundry.db')


@app.route('/')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))

    conn = koneksi()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM transaksi")
    total_transaksi = c.fetchone()[0]

    c.execute("SELECT SUM(total) FROM transaksi WHERE status_pembayaran='Lunas'")
    total_pemasukan = c.fetchone()[0] or 0

    c.execute("SELECT SUM(kasbon) FROM transaksi")
    total_kasbon = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM transaksi WHERE status_pengambilan='Belum Diambil'")
    belum_diambil = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM transaksi WHERE status_pembayaran='Lunas'")
    lunas = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM transaksi WHERE status_pembayaran='Belum Lunas'")
    belum = c.fetchone()[0]

    conn.close()

    status_data = [lunas, belum]

    return render_template('dashboard.html',
                           total_transaksi=total_transaksi,
                           total_pemasukan=total_pemasukan,
                           total_kasbon=total_kasbon,
                           belum_diambil=belum_diambil,
                           status_data=status_data)

@app.route('/transaksi')
def transaksi_list():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = koneksi()
    c = conn.cursor()
    c.execute("SELECT * FROM transaksi ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return render_template('transaksi_list.html', data=data)

@app.route('/transaksi/form', methods=['GET', 'POST'])
def transaksi_form():
    if 'admin' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        nama = request.form['nama']
        no = request.form['no']
        layanan = request.form['layanan']
        berat = float(request.form['berat'])
        diskon = float(request.form['diskon'])
        kasbon = float(request.form['kasbon'])

        harga_per_kg = {
            'Cuci Kering': 7000,
            'Cuci Setrika': 10000,
            'Setrika Saja': 5000
        }.get(layanan, 7000)

        subtotal = berat * harga_per_kg
        total = subtotal - (subtotal * diskon / 100) - kasbon
        tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = koneksi()
        c = conn.cursor()
        c.execute("""INSERT INTO transaksi 
            (nama_pelanggan, no_pelanggan, layanan, berat, diskon, kasbon, total, 
             status_pembayaran, status_pengambilan, tanggal_pemesanan) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Belum Lunas', 'Belum Diambil', ?)""",
            (nama, no, layanan, berat, diskon, kasbon, total, tanggal))
        conn.commit()
        conn.close()
        return redirect(url_for('transaksi_list'))
    return render_template('transaksi_form.html')

@app.route('/transaksi/update/<int:id>', methods=['GET', 'POST'])
def transaksi_update(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = koneksi()
    c = conn.cursor()
    if request.method == 'POST':
        status_bayar = request.form['status_pembayaran']
        status_ambil = request.form['status_pengambilan']
        tanggal_bayar = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status_bayar == 'Lunas' else None
        tanggal_ambil = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status_ambil == 'Sudah Diambil' else None

        c.execute("""UPDATE transaksi SET 
                     status_pembayaran=?, 
                     status_pengambilan=?, 
                     tanggal_pembayaran=?, 
                     tanggal_pengambilan=? 
                     WHERE id=?""",
                  (status_bayar, status_ambil, tanggal_bayar, tanggal_ambil, id))
        conn.commit()
        conn.close()
        return redirect(url_for('transaksi_list'))

    c.execute("SELECT * FROM transaksi WHERE id=?", (id,))
    data = c.fetchone()
    conn.close()
    return render_template('transaksi_update.html', data=data)

@app.route('/laporan')
def laporan():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = koneksi()
    c = conn.cursor()
    c.execute("SELECT tanggal_pemesanan, SUM(total) FROM transaksi GROUP BY tanggal_pemesanan")
    data = c.fetchall()
    conn.close()
    return render_template('laporan.html', data=data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Username atau password salah')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'admin' not in session:
        return redirect(url_for('login'))
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/laporan/excel')
def export_excel():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = koneksi()
    c = conn.cursor()
    c.execute("SELECT * FROM transaksi ORDER BY tanggal_pemesanan")
    data = c.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Laporan Laundry"

    headers = ['ID', 'Nama', 'No HP', 'Layanan', 'Berat', 'Diskon', 'Kasbon', 'Total', 'Status Bayar', 'Status Ambil', 'Tgl Pesan', 'Tgl Bayar', 'Tgl Ambil']
    ws.append(headers)

    for row in data:
        ws.append(row)

    wb.save("laporan_excel.xlsx")
    return send_file("laporan_excel.xlsx", as_attachment=True)

@app.route('/laporan/pdf')
def export_pdf():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = koneksi()
    c = conn.cursor()
    c.execute("SELECT * FROM transaksi ORDER BY tanggal_pemesanan")
    data = c.fetchall()
    conn.close()

    file_name = "laporan_pdf.pdf"
    c_pdf = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4
    y = height - 50

    c_pdf.setFont("Helvetica-Bold", 14)
    c_pdf.drawString(50, y, "Laporan Transaksi Laundry")
    y -= 30
    c_pdf.setFont("Helvetica", 10)

    for row in data:
        text = f"{row[0]} | {row[1]} | {row[3]} | Rp {row[7]} | {row[8]} | {row[9]}"
        c_pdf.drawString(50, y, text)
        y -= 20
        if y < 50:
            c_pdf.showPage()
            y = height - 50

    c_pdf.save()
    return send_file(file_name, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
