from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__)
app.secret_key = 'rahasia_login_admin'  # ganti dengan secret key yang aman
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import sqlite3

app = Flask(__name__)

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
    c.execute("SELECT tanggal_pemesanan, SUM(total) FROM transaksi GROUP BY tanggal_pemesanan ORDER BY tanggal_pemesanan")
    hasil = c.fetchall()
    conn.close()

    labels = [row[0][:10] for row in hasil]  # ambil tanggal saja
    data = [row[1] for row in hasil]

    return render_template('laporan.html', labels=labels, data=data)

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

if __name__ == '__main__':
    app.run(debug=True)




