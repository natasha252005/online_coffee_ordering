BREW & BLISS — ONLINE COFFEE ORDERING SYSTEM
============================================

QUICK START (WINDOWS)
1. Extract this ZIP to a folder such as Desktop\Brew_Bliss_Project.
2. Open the extracted Brew_Bliss_Project folder in VS Code.
3. Double-click START_PROJECT.bat, OR open VS Code Terminal and run:
      python -m pip install -r requirements.txt
      python app.py
4. Open http://127.0.0.1:5000 in your browser.
5. Keep the terminal/window open while using the website. Press Ctrl+C to stop it.

DEMO ADMIN LOGIN
Username: admin
Password: admin123

CUSTOMER FLOW
Register or log in, browse coffee, add items to the cart, apply COFFEE10 or BREW20,
place an order, and review My Orders.

ADMIN FEATURES
Manage coffee records, update order status, and open the DSA Lab.

DATABASE
The application automatically creates brew_bliss.db in this folder on first run.
The database is not included in this ZIP so it can be created cleanly on your computer.

NOTE
This is an educational local prototype. The demo admin password is for local academic use only.
Before public deployment, set a strong SECRET_KEY, replace the demo admin password, and add
production security settings.
