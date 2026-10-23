from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, re
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'brew-bliss-local-demo-change-me')
DB_PATH = os.path.join(os.path.dirname(__file__), 'brew_bliss.db')

COFFEES = [
    ('Espresso','Espresso',99,30,'☕','Deep, bold and beautifully simple.'),
    ('Cappuccino','Cappuccino',129,25,'☕','Velvety milk foam over rich espresso.'),
    ('Cafe Latte','Latte',139,25,'🥛','Smooth espresso with silky steamed milk.'),
    ('Americano','Americano',109,25,'🖤','A clean, balanced coffee classic.'),
    ('Mocha','Mocha',149,20,'🍫','Chocolate, espresso and a little indulgence.'),
    ('Cold Coffee','Cold Coffee',119,20,'🧋','Cool, creamy and ready for sunny days.'),
    ('Caramel Macchiato','Specials',169,15,'🍮','Espresso with a sweet caramel finish.'),
    ('Hazelnut Latte','Specials',159,15,'🌰','Nutty, mellow and wonderfully aromatic.')
]

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def init_db():
    c=db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS admin(admin_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS customer(customer_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL, password TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS coffee(coffee_id INTEGER PRIMARY KEY AUTOINCREMENT, coffee_name TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL, quantity INTEGER NOT NULL DEFAULT 0, emoji TEXT DEFAULT '☕', description TEXT DEFAULT 'Freshly made for you.');
    CREATE TABLE IF NOT EXISTS offers(offer_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, coupon_code TEXT UNIQUE NOT NULL, discount INTEGER NOT NULL, minimum_amount REAL NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS orders(order_id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, total_amount REAL NOT NULL, discount REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(customer_id) REFERENCES customer(customer_id));
    CREATE TABLE IF NOT EXISTS order_items(item_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, coffee_id INTEGER NOT NULL, coffee_name TEXT NOT NULL, quantity INTEGER NOT NULL, unit_price REAL NOT NULL, FOREIGN KEY(order_id) REFERENCES orders(order_id), FOREIGN KEY(coffee_id) REFERENCES coffee(coffee_id));
    ''')
    if not c.execute('SELECT 1 FROM admin WHERE username=?',('admin',)).fetchone():
        c.execute('INSERT INTO admin(username,password) VALUES(?,?)',('admin',generate_password_hash('admin123')))
    if c.execute('SELECT COUNT(*) FROM coffee').fetchone()[0]==0:
        c.executemany('INSERT INTO coffee(coffee_name,category,price,quantity,emoji,description) VALUES(?,?,?,?,?,?)',COFFEES)
    for title,code,disc,minimum in [('First Sip','COFFEE10',10,0),('Brew More','BREW20',20,499)]:
        if not c.execute('SELECT 1 FROM offers WHERE coupon_code=?',(code,)).fetchone():
            c.execute('INSERT INTO offers(title,coupon_code,discount,minimum_amount) VALUES(?,?,?,?)',(title,code,disc,minimum))
    c.commit(); c.close()
init_db()

def login_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a,**kw):
            if session.get('role') != role:
                flash('Please sign in to continue.','error')
                return redirect(url_for('customer_login' if role=='customer' else 'admin_login'))
            return fn(*a,**kw)
        return wrapper
    return deco

def cart_data():
    cart=session.get('cart',{})
    if not cart: return [],0
    c=db(); items=[]; total=0
    for key,qty in cart.items():
        coffee=c.execute('SELECT * FROM coffee WHERE coffee_id=?',(int(key),)).fetchone()
        if coffee and int(qty)>0:
            line=coffee['price']*int(qty); total+=line
            items.append({'coffee':coffee,'qty':int(qty),'line':line})
    c.close(); return items,total

@app.context_processor
def inject_globals():
    return {'cart_count':sum(int(x) for x in session.get('cart',{}).values()), 'current_user':session.get('username'), 'current_role':session.get('role')}

@app.route('/')
def home():
    c=db(); coffees=c.execute('SELECT * FROM coffee ORDER BY coffee_id LIMIT 4').fetchall(); c.close()
    return render_template('index.html',coffees=coffees)

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form.get('username','').strip(); email=request.form.get('email','').strip().lower(); phone=request.form.get('phone','').strip(); address=request.form.get('address','').strip(); password=request.form.get('password',''); confirm=request.form.get('confirm_password','')
        if not re.fullmatch(r'[A-Za-z0-9_]{3,20}',username): flash('Username must be 3–20 letters, numbers or underscores.','error')
        elif not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): flash('Enter a valid email address.','error')
        elif not re.fullmatch(r'\d{10}',phone): flash('Enter a 10-digit phone number.','error')
        elif len(address)<4: flash('Please enter your delivery address.','error')
        elif not re.fullmatch(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}',password): flash('Password must be 8+ characters and include uppercase, lowercase, number and symbol.','error')
        elif password!=confirm: flash('Passwords do not match.','error')
        else:
            c=db()
            try:
                c.execute('INSERT INTO customer(username,email,phone,address,password) VALUES(?,?,?,?,?)',(username,email,phone,address,generate_password_hash(password))); c.commit(); flash('Account created! Please sign in.','success'); c.close(); return redirect(url_for('customer_login'))
            except sqlite3.IntegrityError:
                c.close(); flash('That username or email is already registered.','error')
    return render_template('auth.html',mode='register')

@app.route('/customer/login',methods=['GET','POST'])
def customer_login():
    if request.method=='POST':
        username=request.form.get('username','').strip(); password=request.form.get('password',''); c=db(); user=c.execute('SELECT * FROM customer WHERE username=?',(username,)).fetchone(); c.close()
        if user and check_password_hash(user['password'],password):
            session.clear(); session.update(role='customer',user_id=user['customer_id'],username=user['username'],cart={}); flash('Welcome back! Your next cup is waiting.','success'); return redirect(url_for('customer_home'))
        flash('Incorrect username or password. Please try again.','error')
    return render_template('auth.html',mode='login')

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        username=request.form.get('username','').strip(); password=request.form.get('password',''); c=db(); user=c.execute('SELECT * FROM admin WHERE username=?',(username,)).fetchone(); c.close()
        if user and check_password_hash(user['password'],password):
            session.clear(); session.update(role='admin',username=user['username']); return redirect(url_for('admin_dashboard'))
        flash('Invalid administrator username or password.','error')
    return render_template('auth.html',mode='admin')

@app.route('/customer/home')
@login_required('customer')
def customer_home():
    c=db(); coffees=c.execute('SELECT * FROM coffee WHERE quantity>0 ORDER BY coffee_id').fetchall(); offers=c.execute('SELECT * FROM offers ORDER BY discount DESC').fetchall(); user=c.execute('SELECT * FROM customer WHERE customer_id=?',(session['user_id'],)).fetchone(); c.close()
    return render_template('customer_home.html',coffees=coffees,offers=offers,user=user)

@app.route('/cart/add/<int:coffee_id>',methods=['POST'])
@login_required('customer')
def add_to_cart(coffee_id):
    c=db(); coffee=c.execute('SELECT * FROM coffee WHERE coffee_id=?',(coffee_id,)).fetchone(); c.close()
    if not coffee or coffee['quantity']<1: flash('This coffee is currently unavailable.','error')
    else:
        cart=session.get('cart',{}); key=str(coffee_id); current=int(cart.get(key,0))
        if current>=coffee['quantity']: flash('You have reached the available stock for this coffee.','error')
        else: cart[key]=current+1; session['cart']=cart; session.modified=True; flash(f"{coffee['coffee_name']} added to your cart!",'success')
    return redirect(request.referrer or url_for('customer_home')+'#menu')

@app.route('/cart')
@login_required('customer')
def cart():
    items,total=cart_data(); c=db(); offers=c.execute('SELECT * FROM offers ORDER BY discount DESC').fetchall(); c.close(); code=session.get('coupon_code'); discount=0; selected=None
    if code:
        selected=next((o for o in offers if o['coupon_code']==code),None)
        if selected and total>=selected['minimum_amount']: discount=round(total*selected['discount']/100,2)
        else: session.pop('coupon_code',None); selected=None
    return render_template('cart.html',items=items,total=total,discount=discount,payable=max(0,total-discount),offers=offers,selected=selected)

@app.route('/cart/quantity/<int:coffee_id>/<action>',methods=['POST'])
@login_required('customer')
def quantity(coffee_id,action):
    cart=session.get('cart',{}); key=str(coffee_id); c=db(); coffee=c.execute('SELECT quantity FROM coffee WHERE coffee_id=?',(coffee_id,)).fetchone(); c.close(); qty=int(cart.get(key,0))
    if action=='plus' and coffee and qty<coffee['quantity']: cart[key]=qty+1
    elif action=='minus':
        if qty<=1: cart.pop(key,None)
        else: cart[key]=qty-1
    session['cart']=cart; session.modified=True; return redirect(url_for('cart'))

@app.route('/cart/remove/<int:coffee_id>',methods=['POST'])
@login_required('customer')
def remove_item(coffee_id):
    cart=session.get('cart',{}); cart.pop(str(coffee_id),None); session['cart']=cart; session.modified=True; return redirect(url_for('cart'))

@app.route('/cart/coupon',methods=['POST'])
@login_required('customer')
def coupon():
    code=request.form.get('coupon_code','').strip().upper(); items,total=cart_data(); c=db(); offer=c.execute('SELECT * FROM offers WHERE coupon_code=?',(code,)).fetchone(); c.close()
    if not items: flash('Add coffee to your cart before applying a coupon.','error')
    elif not offer: flash('Coupon code not found.','error')
    elif total<offer['minimum_amount']: flash(f"This coupon needs a cart total of ₹{offer['minimum_amount']:.0f}.",'error')
    else: session['coupon_code']=code; flash(f"{code} applied — {offer['discount']}% off!",'success')
    return redirect(url_for('cart'))

@app.route('/checkout',methods=['POST'])
@login_required('customer')
def checkout():
    items,total=cart_data()
    if not items: flash('Your cart is empty.','error'); return redirect(url_for('customer_home'))
    c=db()
    try:
        c.execute('BEGIN IMMEDIATE')
        for item in items:
            fresh=c.execute('SELECT quantity FROM coffee WHERE coffee_id=?',(item['coffee']['coffee_id'],)).fetchone()
            if not fresh or fresh['quantity']<item['qty']: raise ValueError('Stock changed. Please review your cart.')
        code=session.get('coupon_code'); offer=c.execute('SELECT * FROM offers WHERE coupon_code=?',(code,)).fetchone() if code else None
        discount=round(total*offer['discount']/100,2) if offer and total>=offer['minimum_amount'] else 0
        cur=c.execute('INSERT INTO orders(customer_id,total_amount,discount,status) VALUES(?,?,?,?)',(session['user_id'],round(total-discount,2),discount,'Pending')); order_id=cur.lastrowid
        for item in items:
            coffee=item['coffee']; c.execute('INSERT INTO order_items(order_id,coffee_id,coffee_name,quantity,unit_price) VALUES(?,?,?,?,?)',(order_id,coffee['coffee_id'],coffee['coffee_name'],item['qty'],coffee['price']))
            c.execute('UPDATE coffee SET quantity=quantity-? WHERE coffee_id=?',(item['qty'],coffee['coffee_id']))
        c.commit()
    except ValueError as e:
        c.rollback(); c.close(); flash(str(e),'error'); return redirect(url_for('cart'))
    except Exception:
        c.rollback(); c.close(); flash('Could not place your order. Please try again.','error'); return redirect(url_for('cart'))
    c.close(); session['cart']={}; session.pop('coupon_code',None); return render_template('order_success.html',order_id=order_id,total=round(total-discount,2))

@app.route('/orders')
@login_required('customer')
def orders():
    c=db(); rows=c.execute('SELECT * FROM orders WHERE customer_id=? ORDER BY order_id DESC',(session['user_id'],)).fetchall(); c.close(); return render_template('orders.html',orders=rows)

@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    c=db(); coffees=c.execute('SELECT * FROM coffee ORDER BY coffee_id').fetchall(); orders=c.execute('SELECT orders.*,customer.username FROM orders JOIN customer USING(customer_id) ORDER BY order_id DESC').fetchall(); counts={'coffees':c.execute('SELECT COUNT(*) FROM coffee').fetchone()[0],'orders':c.execute('SELECT COUNT(*) FROM orders').fetchone()[0],'customers':c.execute('SELECT COUNT(*) FROM customer').fetchone()[0]}; c.close(); return render_template('admin_dashboard.html',coffees=coffees,orders=orders,counts=counts)

@app.route('/admin/coffee/save',methods=['POST'])
@login_required('admin')
def save_coffee():
    cid=request.form.get('coffee_id','').strip(); name=request.form.get('coffee_name','').strip(); category=request.form.get('category','Specials').strip(); desc=request.form.get('description','Freshly made for you.').strip(); emoji=request.form.get('emoji','☕').strip() or '☕'
    try: price=float(request.form.get('price','0')); stock=int(request.form.get('quantity','0'))
    except ValueError: flash('Price and stock must be numbers.','error'); return redirect(url_for('admin_dashboard')+'#manage-coffee')
    if not name or price<=0 or stock<0: flash('Enter a name, positive price and non-negative stock.','error')
    else:
        c=db()
        if cid: c.execute('UPDATE coffee SET coffee_name=?,category=?,price=?,quantity=?,emoji=?,description=? WHERE coffee_id=?',(name,category,price,stock,emoji,desc,cid)); flash('Coffee updated.','success')
        else: c.execute('INSERT INTO coffee(coffee_name,category,price,quantity,emoji,description) VALUES(?,?,?,?,?,?)',(name,category,price,stock,emoji,desc)); flash('New coffee added.','success')
        c.commit(); c.close()
    return redirect(url_for('admin_dashboard')+'#manage-coffee')

@app.route('/admin/coffee/delete/<int:coffee_id>',methods=['POST'])
@login_required('admin')
def delete_coffee(coffee_id):
    c=db(); used=c.execute('SELECT 1 FROM order_items WHERE coffee_id=?',(coffee_id,)).fetchone()
    if used: c.execute('UPDATE coffee SET quantity=0 WHERE coffee_id=?',(coffee_id,)); flash('This coffee is in order history, so it was marked out of stock instead of being deleted.','success')
    else: c.execute('DELETE FROM coffee WHERE coffee_id=?',(coffee_id,)); flash('Coffee deleted.','success')
    c.commit(); c.close(); return redirect(url_for('admin_dashboard')+'#manage-coffee')

@app.route('/admin/order/status/<int:order_id>',methods=['POST'])
@login_required('admin')
def order_status(order_id):
    status=request.form.get('status','Pending'); allowed={'Pending','Preparing','Ready','Completed','Cancelled'}
    if status in allowed:
        c=db(); c.execute('UPDATE orders SET status=? WHERE order_id=?',(status,order_id)); c.commit(); c.close(); flash('Order status updated.','success')
    return redirect(url_for('admin_dashboard')+'#orders')

# DSA Lab: functional demonstrations for all four phases.
@app.route('/dsa')
@login_required('admin')
def dsa():
    c=db(); coffees=c.execute('SELECT * FROM coffee ORDER BY coffee_id').fetchall(); offers=c.execute('SELECT * FROM offers ORDER BY discount DESC').fetchall(); c.close()
    # Linked-list traversal represented by current menu records.
    linked=' → '.join(x['coffee_name'] for x in coffees) + (' → NULL' if coffees else 'NULL')
    # BST insertion/traversals over coffee prices.
    class Node:
        def __init__(self,v): self.v=v; self.l=None; self.r=None
    def insert(root,v):
        if root is None: return Node(v)
        if v<root.v: root.l=insert(root.l,v)
        else: root.r=insert(root.r,v)
        return root
    root=None
    for x in coffees: root=insert(root,x['price'])
    def walk(n,order,out):
        if not n:return
        if order=='pre':out.append(n.v)
        walk(n.l,order,out)
        if order=='in':out.append(n.v)
        walk(n.r,order,out)
        if order=='post':out.append(n.v)
    traversals={}
    for key,label in [('pre','Preorder'),('in','Inorder'),('post','Postorder')]:
        out=[]; walk(root,key,out); traversals[label]=out
    graph={'Hot Coffee':['Espresso','Cappuccino','Cafe Latte','Americano'],'Specials':['Mocha','Caramel Macchiato','Hazelnut Latte'],'Cold Coffee':['Cold Coffee']}
    start='Hot Coffee'; seen={start}; queue=[start]; bfs=[]
    while queue:
        node=queue.pop(0); bfs.append(node)
        for nxt in graph.get(node,[]):
            if nxt not in seen: seen.add(nxt); queue.append(nxt)
    prices=sorted([x['price'] for x in coffees]); target=prices[len(prices)//2] if prices else 0
    # Greedy: choose highest eligible immediate discount for a sample cart value.
    sample_total=600; eligible=[o for o in offers if sample_total>=o['minimum_amount']]; best=max(eligible,key=lambda o:o['discount']) if eligible else None
    return render_template('dsa.html',coffees=coffees,linked=linked,traversals=traversals,bfs=bfs,prices=prices,target=target,best=best,sample_total=sample_total)

@app.route('/logout')
def logout(): session.clear(); flash('You have been signed out. See you soon!','success'); return redirect(url_for('home'))

if __name__=='__main__': app.run(debug=True)
