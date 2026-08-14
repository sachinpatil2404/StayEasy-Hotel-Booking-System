# 🏨 StayEasy - Full-Stack Multi-Tenant Hotel Reservation & Analytics Platform

**StayEasy** is a modern, enterprise-grade Django web application designed for online hotel reservations, multi-tenant property management, interactive room availability scheduling, real-time business analytics, and dynamic PDF invoice generation.

---

## 🌟 Key Features

### 1. 👥 Multi-Tenant Role & Data Isolation
* **Role Selection**: Toggle between **Guest / Customer** (browse & book rooms) and **Hotel Manager / Admin** (manage properties & analytics).
* **Strict Data Scoping**: Multi-tenant data filtering (`owner = request.user`) ensures Hotel Managers can access only their own hotels, rooms, bookings, and revenue metrics.

### 2. 📊 Real-Time Analytics & Data Visualization
* **Chart.js Visualizations**:
  * **Monthly & Annual Revenue Trends**: Dual-axis line and bar chart displaying earnings and booking counts over time.
  * **Booking Status Ratio**: Doughnut chart showing Confirmed vs. Cancelled booking ratios.
  * **Revenue by Room Type**: Category breakdown across Single, Double, Deluxe, and Suite rooms.
* **Period Toggle Filters**: Switch between **Month-wise** (Last 6 Months) and **Year-wise** (Annual) analytics.
* **6-Metric Stat Summary Cards**: Live metrics for Total Revenue (₹), Confirmed Bookings, Cancelled Bookings, Total Hotels, Total Rooms, and Guests Served.

### 3. 📅 Interactive Room Availability Calendar (`FullCalendar.js`)
* Visual grid view at `/admin-dashboard/calendar/` rendering room occupancy timelines, check-in dates, and check-out deadlines.
* Color-coded event statuses (**Emerald Green = Confirmed**, **Red = Cancelled**).
* Interactive Event Detail Modals displaying customer info, stay duration, total price, and status.

### 4. 💱 Dynamic Multi-Currency Engine
* Navbar currency selector supporting **INR (₹)**, **USD ($)**, and **EUR (€)**.
* Session-based real-time currency converter updating room rates, checkout totals, and booking summaries across all pages.

### 5. 🧾 Automated PDF Invoice & QR Receipt Generation
* Server-side PDF invoice compiler using `ReportLab`.
* Includes itemized stay charges, customer details, hotel info, and embedded QR verification codes.

### 6. ⭐ Hotel Rating, Reviews & Amenity Tagging
* Interactive 1–5 star rating picker and review system.
* Amenity badges for **Air Conditioned (AC)**, **Free High-Speed WiFi**, and **Complimentary Breakfast**.
* Room multi-photo upload and photo deletion gallery.

---

## 🛠️ Technology Stack

* **Backend**: Python 3.14+, Django 6.0+
* **Frontend**: HTML5, CSS3 (Vanilla CSS System), JavaScript (ES6+)
* **Data Visualization**: Chart.js, FullCalendar.js (v6)
* **Document Engine**: ReportLab (PDF Generation), QRCode
* **Database**: MySQL (environment-based configuration)
* **Icons & Styling**: FontAwesome 6, Google Fonts (Inter / Outfit)

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.10 or higher installed
* `pip` package manager

### 1. Clone the Repository
```bash
git clone https://github.com/sachinpatil2404/StayEasy-Hotel-Booking-System.git
cd StayEasy-Hotel-Booking-System
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver
```

Open your browser and navigate to `http://127.0.0.1:8000/`.

---

## 📁 Project Directory Structure

```text
hotel_book1/
├── bookings/
│   ├── models.py             # Hotel, Room, Booking, UserProfile, HotelRating models
│   ├── views.py              # Views for authentication, booking, admin panel & analytics
│   ├── urls.py               # Application URL routing
│   ├── forms.py              # BookingForm, RegisterForm, ProfileImageForm
│   ├── templatetags/         # Custom currency tags (currency_tags.py)
│   └── templates/bookings/   # HTML templates for home, room list, admin dashboard, etc.
├── hotel_book1/
│   ├── settings.py           # Project configurations & login redirect URLs
│   ├── urls.py               # Main URL configuration
│   └── wsgi.py               # WSGI entrypoint for deployment
├── media/                    # User uploaded hotel images and profile photos
├── static/                   # CSS stylesheets, JavaScript files, video backgrounds
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

