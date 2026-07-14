# Retail Storefront App

A simple, self-hosted web application for a retail storefront. Customers can register, log in, browse inventory, and place orders. The owner (admin) manages products, views orders, and processes payments separately outside the app.

## Features
- **Customer Portal**: Login/register, view real-time inventory, build cart, place orders.
- **Admin Dashboard**: Manage products (add/edit/delete/update stock), view all customer orders, update order status (pending → paid → fulfilled), see notifications for new orders.
- **Order Flow**: Customers place orders (no payment in app). Owner notified via admin panel (pending orders highlighted). Process payment offline (e.g., Venmo, cash, invoice), then update status in app.
- **Inventory Control**: Stock levels update on order placement. Low stock warnings for admin.
- **Secure**: Password hashing, role-based access (customer vs admin), login required for sensitive pages.
- **Responsive**: Works on desktop and mobile browsers.

## Tech Stack
- Python + Flask (backend)
- SQLite (database, file-based, no server needed)
- Bootstrap 5 (UI)
- Vanilla JS (dynamic cart)

## Quick Start (Local Development)

1. **Clone or download** this folder to your computer.

2. **Create virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**:
   ```bash
   python app.py
   ```
   Open browser to http://127.0.0.1:5000

5. **First time setup**:
   - The app auto-creates `retail_app.db` SQLite file.
   - A default **admin account** is created on first run:
     - Email: `admin@yourstore.com`
     - Password: `admin123`  ← **CHANGE THIS IMMEDIATELY** after first login!
   - Register customer accounts via the site (or add more admins manually in code/DB).

6. **Deploying**:
   - For production: Use Gunicorn + Nginx, or deploy to Render.com, Railway, or Heroku (free tier possible).
   - Set `SECRET_KEY` and `FLASK_ENV=production` via environment variables.
   - Change admin password and consider adding more security (HTTPS, rate limiting).

## How to Use

### For Customers:
1. Go to home → Register or Login.
2. Browse **Shop** → See current inventory with stock levels.
3. Use checkboxes + quantity fields to select items.
4. Click "Add to Cart" → Review/edit cart in modal.
5. Fill customer details if needed → **Place Order**.
6. Order goes to "Pending". You can view your order history in "My Orders".
7. Owner will contact you to complete payment (outside app).

### For Owner/Admin:
1. Login with admin credentials.
2. **Dashboard**: Overview + pending orders count (notifications!).
3. **Manage Products**: Add new items, edit prices/descriptions, adjust stock, delete.
4. **View Orders**: See all orders, click to expand details (items, customer info). Change status as you process payment/fulfill.
5. Stock auto-deducts on order; add back if you cancel an order.

## Customization
- **Store Name/Branding**: Edit `app.py` (STORE_NAME, contact info) and templates.
- **Add your logo**: Replace or add in `static/` and update base.html.
- **Product Categories**: Extend Product model if needed.
- **Email Notifications**: (Advanced) Integrate Flask-Mail + SMTP for order confirmations to customers and alerts to you.
- **Payment**: Currently manual. Later integrate Stripe/PayPal for full checkout if desired.
- **Images**: Add `image_url` field to products; host images or use placeholders/unsplash.

## Database
- File: `retail_app.db` (in project root after first run).
- Tables: users, products, orders, order_items.
- To inspect: Use DB Browser for SQLite or `sqlite3 retail_app.db`.

## Security Notes
- Change default admin password immediately.
- Use strong unique passwords.
- For public internet: Put behind reverse proxy with HTTPS (Let's Encrypt free).
- Never commit real secrets or the .db file with real data to git.
- This is a starter app — audit before handling real payments/customer data.

## Troubleshooting
- Port in use? Change in `app.py`: `app.run(port=5001)`
- DB issues? Delete `retail_app.db` and restart (recreates with seed data).
- JS cart not working? Check browser console (F12).
- Need help extending? Provide more details on products, branding, or extra features (e.g. search, filters, reports).

Built for easy local/self-hosted use. Enjoy your retail business! 

**Default Admin**: admin@yourstore.com / admin123 (change ASAP)
