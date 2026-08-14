import os
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User

def custom_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("login")
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from datetime import datetime, timedelta
from .forms import RegisterForm, BookingForm, ProfileImageForm
from .models import UserProfile, Hotel, Room, Booking, RoomImage, HotelRating
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
import qrcode
import io
from io import BytesIO
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

def set_currency(request):
    if request.method == "POST":
        curr = request.POST.get("currency", "INR")
        if curr in ["INR", "USD", "EUR"]:
            request.session["currency"] = curr
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
        return redirect(next_url)
    return redirect("home")


def is_admin(user):
    return user.is_staff or user.is_superuser


@user_passes_test(is_admin, login_url='/login/')
def admin_calendar(request):
    return render(request, "bookings/admin_calendar.html")


@user_passes_test(is_admin, login_url='/login/')
def admin_calendar_events_api(request):
    if request.user.is_superuser:
        bookings = Booking.objects.select_related('user', 'room', 'room__hotel').all()
    else:
        my_hotels = Hotel.objects.filter(owner=request.user)
        bookings = Booking.objects.filter(room__hotel__in=my_hotels).select_related('user', 'room', 'room__hotel')

    events = []
    for b in bookings:
        color = '#10b981' if b.status == 'confirmed' else '#ef4444'
        title = f"Room {b.room.room_number} ({b.user.username})"
        events.append({
            'id': b.id,
            'title': title,
            'start': b.check_in.strftime('%Y-%m-%d'),
            'end': (b.check_out + timedelta(days=1)).strftime('%Y-%m-%d'),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'customer': b.user.username,
                'hotel': b.room.hotel.name,
                'room_number': b.room.room_number,
                'room_type': b.room.room_type,
                'status': b.status.capitalize(),
                'price': float(b.total_price or 0),
                'guests': b.guests,
                'check_in': b.check_in.strftime('%d %b %Y'),
                'check_out': b.check_out.strftime('%d %b %Y'),
            }
        })
    return JsonResponse(events, safe=False)

def home(request):
    query = request.GET.get("city") or request.GET.get("query") or ""
    if query:
        hotels = Hotel.objects.filter(
            Q(city__icontains=query) |
            Q(name__icontains=query) |
            Q(address__icontains=query)
        )
    else:
        hotels = Hotel.objects.all()
    return render(request, "bookings/home.html", {"hotels": hotels, "query": query})


def room_list(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    rooms = hotel.rooms.all()
    user_rating = None
    if request.user.is_authenticated:
        user_rating = HotelRating.objects.filter(hotel=hotel, user=request.user).first()
    return render(request, "bookings/room_list.html", {
        "hotel": hotel,
        "rooms": rooms,
        "user_rating": user_rating
    })

@login_required
def rate_hotel(request, hotel_id):
    if request.method == "POST":
        hotel = get_object_or_404(Hotel, id=hotel_id)
        try:
            rating_val = int(request.POST.get("rating", 5))
        except (ValueError, TypeError):
            rating_val = 5
        review_text = request.POST.get("review", "")

        HotelRating.objects.update_or_create(
            hotel=hotel,
            user=request.user,
            defaults={"rating": rating_val, "review": review_text}
        )
        messages.success(request, f"Thank you! Your {rating_val}★ rating for {hotel.name} has been recorded.")
    return redirect("room_list", hotel_id=hotel_id)


def custom_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("admin_dashboard")
        return redirect("dashboard")

    if request.method == "POST":
        u = request.POST.get("username")
        p = request.POST.get("password")
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            if user.is_staff:
                return redirect("admin_dashboard")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "bookings/login.html")


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            
            # Handle role: manager vs customer
            role = form.cleaned_data.get("role", "customer")
            if role == "manager":
                user.is_staff = True
                
            user.save()

            # Save phone number
            phone = form.cleaned_data.get("phone", "")
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone = phone
            profile.save()

            if role == "manager":
                messages.success(request, "Hotel Manager account created! Please log in to access your Admin Panel.")
            else:
                messages.success(request, "Account created! Please log in.")

            return redirect("login")
    else:
        form = RegisterForm()

    return render(request, "bookings/register.html", {"form": form})
@login_required(login_url='/login/')
def book_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    if request.method == "POST":
        form = BookingForm(request.POST)

        if form.is_valid():
            try:
                booking = form.save(commit=False)
                booking.room = room
                booking.user = request.user
                booking.status = 'confirmed'
                booking.payment_status = 'Pending'
                booking.save()

                messages.success(request, f"Room {room.room_number} reserved! Please complete your payment.")
                return redirect("fake_payment", booking_id=booking.id)

            except ValidationError as e:
                err_msg = e.messages[0] if hasattr(e, 'messages') and e.messages else "This room is already booked for selected dates."
                form.add_error(None, err_msg)
    else:
        form = BookingForm()

    return render(request, "bookings/book_room.html", {
        "form": form,
        "room": room
    })
def booking_success(request):
    return render(request, "bookings/booking_success.html")


def check_availability(request):
    room_id = request.GET.get('room_id')
    check_in_str = request.GET.get('check_in')
    check_out_str = request.GET.get('check_out')

    if not room_id or not check_in_str or not check_out_str:
        return JsonResponse({'available': False, 'error': 'Missing parameters'})

    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()

        if check_out <= check_in:
            return JsonResponse({'available': False, 'error': 'Check-out must be after Check-in'})

        overlapping = Booking.objects.filter(
            room_id=room_id,
            status='confirmed',
            check_in__lt=check_out,
            check_out__gt=check_in
        ).exists()

        return JsonResponse({'available': not overlapping})
    except Exception as e:
        return JsonResponse({'available': False, 'error': str(e)})
@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user)
    return render(request, "bookings/my_bookings.html", {"bookings": bookings
                                                         , "today": timezone.now().date()})

# Optional: Twilio (install twilio package and set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM in env)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except Exception:
    TWILIO_AVAILABLE = False

@login_required(login_url='/login/')
def payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, "bookings/fake_payment.html", {
        "booking": booking
    })

@login_required
def payment_confirm(request, room_id):

    if request.method != "POST":
        return redirect("home")

    room = get_object_or_404(Room, id=room_id)

    check_in_str = request.POST.get("check_in")
    check_out_str = request.POST.get("check_out")
    guests_str = request.POST.get("guests")

    # Validation
    if not check_in_str or not check_out_str or not guests_str:
        messages.error(request, "Missing booking information.")
        return redirect("home")

    try:
        check_in = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out = datetime.strptime(check_out_str, "%Y-%m-%d").date()
        guests = int(guests_str)
    except Exception:
        messages.error(request, "Invalid booking data.")
        return redirect("home")

    # Create booking
    booking = Booking.objects.create(
        room=room,
        user=request.user,
        check_in=check_in,
        check_out=check_out,
        guests=guests
    )

    # Room label
    room_label = room.room_number

    # SEND ITEMIZED BILL & RECEIPT EMAIL WITH PDF ATTACHMENT
    try:
        send_booking_email(request.user, booking)
        print("INVOICE EMAIL SENT SUCCESSFULLY")
    except Exception as e:
        print("EMAIL ERROR:", e)
        messages.warning(request, "Booking saved but email could not be sent.")

    return redirect("booking_success")
# @login_required
# def dashboard(request):
#     user = request.user
#
#     # KPIs
#     total_bookings = Booking.objects.filter(user=user).count()
#     upcoming_bookings = Booking.objects.filter(user=user, check_in__gte=timezone.now().date()).count()
#     total_spend = Booking.objects.filter(user=user).aggregate(total=Sum('total_price'))['total'] or 0
#
#     # recent bookings (last 8)
#     recent_bookings = Booking.objects.filter(user=user).order_by('-check_in')[:8]
#
#     # Chart data: bookings per day for last 14 days (example)
#     today = timezone.now().date()
#     days = []
#     counts = []
#     for i in range(13, -1, -1):   # 14 days (oldest->newest)
#         day = today - timedelta(days=i)
#         days.append(day.strftime("%b %d"))  # label
#         counts.append(Booking.objects.filter(user=user, check_in=day).count())
#
#     # Quick hotel summary (hotels you booked)
#     hotels_booked = Hotel.objects.filter(rooms__bookings__user=user).distinct()
#
#     context = {
#         "total_bookings": total_bookings,
#         "upcoming_bookings": upcoming_bookings,
#         "total_spend": total_spend,
#         "recent_bookings": recent_bookings,
#         "chart_labels": days,
#         "chart_data": counts,
#         "hotels_booked": hotels_booked,
#     }
#     context["hide_navbar"] = True
#     return render(request, "bookings/profile_dashboard.html", context)

@login_required
def dashboard(request):
    user = request.user

    # =========================
    # KPIs
    # =========================
    total_bookings = Booking.objects.filter(user=user).count()

    upcoming_bookings = Booking.objects.filter(
        user=user,
        check_in__gte=timezone.now().date()
    ).count()

    total_spend = Booking.objects.filter(user=user).aggregate(
        total=Sum('total_price')
    )['total'] or 0

    # =========================
    # Recent bookings
    # =========================
    recent_bookings = Booking.objects.filter(user=user).order_by('-check_in')[:8]

    # =========================
    # 🔥 FIXED SMART CHART LOGIC
    # =========================

    latest_booking = Booking.objects.filter(user=user).order_by('-check_in').first()

    if latest_booking:
        base_date = latest_booking.check_in
    else:
        base_date = timezone.now().date()

    # Show 7 days before + 7 days after
    start_date = base_date - timedelta(days=7)
    end_date = base_date + timedelta(days=7)

    days = []
    counts = []

    current = start_date
    while current <= end_date:
        days.append(current.strftime("%b %d"))

        count = Booking.objects.filter(
            user=user,
            check_in__lte=current,
            check_out__gte=current
        ).count()

        counts.append(count)
        current += timedelta(days=1)

    # =========================
    # Hotels booked
    # =========================
    hotels_booked = Hotel.objects.filter(
        rooms__bookings__user=user
    ).distinct()

    context = {
        "total_bookings": total_bookings,
        "upcoming_bookings": upcoming_bookings,
        "total_spend": total_spend,
        "recent_bookings": recent_bookings,
        "chart_labels": days,
        "chart_data": counts,
        "hotels_booked": hotels_booked,
        "hide_navbar": True,
    }
    return render(request, "bookings/profile_dashboard.html", context)
@csrf_exempt
def newsletter_subscribe(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=400)
    data = json.loads(request.body or '{}')
    email = data.get('email')
    if not email:
        return JsonResponse({'ok': False, 'error':'missing'}, status=400)
    # save to DB or send to mailchimp/sendgrid here
    return JsonResponse({'ok': True})
def check_availability(request):
    room_id = request.GET.get("room_id")
    check_in = request.GET.get("check_in")
    check_out = request.GET.get("check_out")

    if not (room_id and check_in and check_out):
        return JsonResponse({"available": False})

    overlapping = Booking.objects.filter(
        room_id=room_id,
        check_in__lt=check_out,
        check_out__gt=check_in,
    )

    return JsonResponse({
        "available": not overlapping.exists()
    })
@login_required
def booking_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    return render(request, "bookings/receipt.html", {
        "booking": booking
    })

def generate_pdf_invoice_buffer(user, booking):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    elements = []

    logo_path = os.path.join(settings.BASE_DIR, "static/images/logo.png")
    if os.path.exists(logo_path):
        logo = RLImage(logo_path, width=50, height=50)
        header_data = [[logo, "StayEasy", "INVOICE & RECEIPT"]]
        col_widths = [60, 250, 140]
    else:
        header_data = [["StayEasy", "INVOICE & RECEIPT"]]
        col_widths = [310, 140]

    header = Table(header_data, colWidths=col_widths, rowHeights=[60])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#4e63ff")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (-1, 0), (-1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))

    elements.append(header)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("<b>BOOKING INVOICE & PAYMENT RECEIPT</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"Invoice ID: INV-{booking.id}", normal_style))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%d %b %Y %I:%M %p')}", normal_style))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("<b>Customer Information</b>", styles['Heading3']))
    elements.append(Paragraph(f"Customer Name: {user.username}", normal_style))
    elements.append(Paragraph(f"Email: {user.email}", normal_style))
    elements.append(Spacer(1, 15))

    table_data = [
        ["Product / Service", "Details", "Amount"],
        [
            f"{booking.room.hotel.name}\nRoom: {booking.room.room_type} (#{booking.room.room_number})",
            f"Check-in: {booking.check_in}\nCheck-out: {booking.check_out}\nGuests: {booking.guests}",
            f"₹ {booking.total_price}"
        ]
    ]

    table = Table(table_data, colWidths=[200, 150, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4e63ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    total_table = Table([
        ["Payment Method: Online (Paid)", f"Total Paid: ₹ {booking.total_price}"]
    ], colWidths=[220, 230])

    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#22c55e")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(total_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def send_booking_email(user, booking):
    if not user.email:
        print("Cannot send booking email: User email is empty.")
        return False

    subject = f"🧾 Booking Invoice & Order Receipt #{booking.id} - StayEasy"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
        .invoice-card {{ max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
        .header {{ background: linear-gradient(135deg, #4e63ff, #2563eb); color: #ffffff; padding: 30px 25px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; letter-spacing: 0.5px; }}
        .header p {{ margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }}
        .body {{ padding: 25px; }}
        .status-badge {{ display: inline-block; background: #dcfce7; color: #15803d; font-size: 12px; font-weight: 700; padding: 5px 14px; border-radius: 20px; text-transform: uppercase; margin-bottom: 15px; }}
        .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        .info-table td {{ padding: 6px 0; font-size: 14px; color: #475569; }}
        .info-table td strong {{ color: #1e293b; }}
        .bill-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px; }}
        .bill-table th {{ background: #f8fafc; color: #475569; text-align: left; padding: 12px; font-size: 13px; text-transform: uppercase; border-bottom: 2px solid #e2e8f0; }}
        .bill-table td {{ padding: 14px 12px; border-bottom: 1px solid #e2e8f0; font-size: 14px; color: #334155; vertical-align: top; }}
        .total-box {{ background: #f1f5f9; padding: 18px; border-radius: 8px; text-align: right; font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 15px; }}
        .total-box span {{ color: #2563eb; font-size: 24px; font-weight: 800; }}
        .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 13px; color: #64748b; border-top: 1px solid #e2e8f0; }}
      </style>
    </head>
    <body>
      <div class="invoice-card">
        <div class="header">
          <h1>StayEasy</h1>
          <p>Official Order Bill & Payment Receipt</p>
        </div>
        <div class="body">
          <div class="status-badge">✓ Payment Confirmed</div>
          <p>Hello <strong>{user.username}</strong>,</p>
          <p>Thank you for your booking! Below is your itemized order bill and payment receipt. Your official downloadable PDF invoice is attached to this email.</p>
          
          <table class="info-table">
            <tr>
              <td><strong>Invoice Number:</strong> INV-{booking.id}</td>
              <td style="text-align:right;"><strong>Order Date:</strong> {datetime.now().strftime('%d %b %Y')}</td>
            </tr>
            <tr>
              <td><strong>Billed To:</strong> {user.username} ({user.email})</td>
              <td style="text-align:right;"><strong>Payment Status:</strong> Paid</td>
            </tr>
          </table>

          <table class="bill-table">
            <thead>
              <tr>
                <th>Item / Hotel Reservation</th>
                <th>Stay Details</th>
                <th style="text-align:right;">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <strong>{booking.room.hotel.name}</strong><br>
                  <small style="color:#64748b;">{booking.room.room_type} (Room #{booking.room.room_number})</small>
                </td>
                <td>
                  Check-in: {booking.check_in}<br>
                  Check-out: {booking.check_out}<br>
                  Guests: {booking.guests} Person(s)
                </td>
                <td style="text-align:right; font-weight:700;">₹{booking.total_price}</td>
              </tr>
            </tbody>
          </table>

          <div class="total-box">
            Total Amount Paid: <span>₹{booking.total_price}</span>
          </div>

          <div style="text-align: center; margin-top: 25px;">
            <p style="font-size: 13px; color: #64748b; margin-bottom: 5px;">📄 <strong>Attachment Included:</strong> Your official PDF Invoice Receipt (<code>StayEasy_Invoice_{booking.id}.pdf</code>) is attached below.</p>
          </div>
        </div>
        <div class="footer">
          <p>Thank you for choosing <strong>StayEasy Hotel Bookings</strong>!</p>
          <p style="margin-top:5px; font-size:11px; color:#94a3b8;">© StayEasy Inc. All Rights Reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """

    # Generate PDF Invoice Attachment
    pdf_bytes = None
    try:
        pdf_bytes = generate_pdf_invoice_buffer(user, booking)
    except Exception as e:
        print("PDF ATTACHMENT EXCEPTION:", e)

    # 1. Try Resend HTTP API first (bypasses Render Free SMTP port block)
    if getattr(settings, 'RESEND_API_KEY', '') or os.getenv('RESEND_API_KEY', ''):
        from .email_service import send_email_via_resend
        attachments = []
        if pdf_bytes:
            attachments.append((f"StayEasy_Invoice_{booking.id}.pdf", pdf_bytes, "application/pdf"))
        success = send_email_via_resend(subject, html_content, [user.email], attachments=attachments)
        if success:
            print(f"INVOICE & RECEIPT EMAIL SENT VIA RESEND HTTP API to {user.email}")
            return True

    # 2. Fallback to Django EmailMessage (SMTP)
    try:
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.content_subtype = "html"
        if pdf_bytes:
            email.attach(f"StayEasy_Invoice_{booking.id}.pdf", pdf_bytes, "application/pdf")
        email.send(fail_silently=False)
        print(f"INVOICE & RECEIPT EMAIL SENT SUCCESSFULLY to {user.email}")
        return True
    except Exception as e:
        print("INVOICE EMAIL SEND EXCEPTION:", e)
        return False

def send_user_email(user, subject, html_content):
    if not user.email:
        return

    # Try Resend HTTP API first
    if getattr(settings, 'RESEND_API_KEY', '') or os.getenv('RESEND_API_KEY', ''):
        from .email_service import send_email_via_resend
        if send_email_via_resend(subject, html_content, [user.email]):
            return

    # Fallback to Django EmailMessage
    try:
        email = EmailMessage(
            subject,
            html_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        email.content_subtype = "html"
        email.send()
    except Exception as e:
        print(f"send_user_email exception: {e}")


def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            # SEND EMAIL
            html_content = f"""
            <h2>Login Alert 🔐</h2>
            <p>Hello <strong>{user.username}</strong>,</p>
            <p>You logged in successfully.</p>
            """

            send_user_email(user, "Login Alert", html_content)

            messages.success(request, "Login successful!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid credentials")

    return render(request, "bookings/login.html")

# @login_required
# def update_profile(request):
#     profile = request.user.userprofile
#
#     if request.method == "POST":
#         if request.FILES.get('profile_image'):
#             profile.profile_image = request.FILES['profile_image']
#             profile.save()
#
#             messages.success(request, "Profile updated successfully!")
#             return redirect("dashboard")
#
#     return render(request, "bookings/update_profile.html", {
#         "profile": profile
#     })
@login_required
def upload_profile_image(request):
    profile = request.user.userprofile

    if request.method == "POST":
        form = ProfileImageForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = ProfileImageForm(instance=profile)

    return render(request, "bookings/upload_profile.html", {"form": form})
@login_required
def fake_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, "bookings/fake_payment.html", {"booking": booking})


@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    booking.payment_status = "Paid"
    booking.save()

    # SEND ITEMIZED BILL & RECEIPT EMAIL WITH PDF ATTACHMENT
    try:
        send_booking_email(request.user, booking)
    except Exception as e:
        print("PAYMENT SUCCESS EMAIL EXCEPTION:", e)

    return render(request, "bookings/payment_success.html", {"booking": booking})







@login_required
def download_invoice(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{booking.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'title',
        fontSize=18,
        textColor=colors.white,
        alignment=TA_CENTER,
        leading=22  # ✅ fixes vertical spacing
    )

    normal_style = styles['Normal']

    elements = []

    logo_path = os.path.join(settings.BASE_DIR, "static/images/logo.png")
    logo = RLImage(logo_path, width=50, height=50)

    header = Table([
        [logo, "StayEasy", "INVOICE"]
    ], colWidths=[60, 250, 140], rowHeights=[60])

    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#4e63ff")),
        ('TEXTCOLOR', (1, 0), (2, 0), colors.white),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))

    elements.append(header)
    elements.append(Spacer(1, 20))

    # =========================
    # INVOICE TITLE
    # =========================
    elements.append(Paragraph("<b>BOOKING INVOICE</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))

    # =========================
    # INVOICE DETAILS
    # =========================
    elements.append(Paragraph(f"Invoice ID: INV-{booking.id}", normal_style))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%d %b %Y')}", normal_style))
    elements.append(Spacer(1, 15))

    # =========================
    # CUSTOMER INFO
    # =========================
    elements.append(Paragraph("<b>Customer Details</b>", styles['Heading3']))
    elements.append(Paragraph(f"Name: {request.user.username}", normal_style))
    elements.append(Paragraph(f"Email: {request.user.email}", normal_style))
    elements.append(Spacer(1, 15))

    # =========================
    # BOOKING TABLE (PREMIUM)
    # =========================
    table_data = [
        ["Field", "Details"],
        ["Booking ID", f"#{booking.id}"],
        ["Hotel", booking.room.hotel.name],
        ["Room", f"{booking.room.room_type} ({booking.room.room_number})"],
        ["Check-in", str(booking.check_in)],
        ["Check-out", str(booking.check_out)],
        ["Payment Method", "Razorpay (Test Mode)"],
        ["Status", "PAID"],
    ]

    table = Table(table_data, colWidths=[160, 290])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4e63ff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),

        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),

        ('PADDING', (0, 0), (-1, -1), 10),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # =========================
    # TOTAL SECTION (HIGHLIGHT)
    # =========================
    total_table = Table(
        [["Total Paid", f"₹ {booking.total_price}"]],
        colWidths=[200, 250]
    )

    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#22c55e")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))

    elements.append(total_table)


    # =========================
    # QR CODE GENERATION
    # =========================

    booking_url = request.build_absolute_uri(
        reverse("booking_receipt", args=[booking.id])
    )

    qr = qrcode.make(booking_url)

    buffer = io.BytesIO()
    qr.save(buffer)
    buffer.seek(0)

    qr_image = RLImage(buffer, width=120, height=120)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Scan to View Booking</b>", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(qr_image)
    elements.append(Spacer(1, 30))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "Thank you for choosing <b>StayEasy</b> ♥",
        styles['Normal']
    ))
    elements.append(Spacer(1, 10))
    # =========================
    # FOOTER
    # =========================
    elements.append(Paragraph(
        "Thank you for choosing <b>StayEasy</b> ❤️",
        styles['Normal']
    ))
    # =========================
    # QR CODE DATA
    # =========================
    qr_data = f"""
    StayEasy Booking
    Booking ID: {booking.id}
    User: {request.user.username}
    Hotel: {booking.room.hotel.name}
    Room: {booking.room.room_type}
    Check-in: {booking.check_in}
    Check-out: {booking.check_out}
    Amount: ₹{booking.total_price}
    """

    qr = qrcode.make(qr_data)

    buffer = io.BytesIO()
    qr.save(buffer)
    buffer.seek(0)

    qr_image = RLImage(buffer, width=120, height=120)

    doc.build(elements)

    return response

def search_hotels(request):
    query = request.GET.get('q')

    if query:
        hotels = Hotel.objects.filter(city__icontains=query)
    else:
        hotels = Hotel.objects.all()

    return render(request, "bookings/search_results.html", {
        "hotels": hotels,
        "query": query
    })

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # ❌ Already cancelled
    if booking.status == 'cancelled':
        messages.error(request, "Booking already cancelled.")
        return redirect('my_bookings')

    # ❌ Cannot cancel after check-in
    if booking.check_in <= timezone.now().date():
        messages.error(request, "You cannot cancel after check-in date.")
        return redirect('my_bookings')

    # ✅ Cancel booking
    booking.status = 'cancelled'
    booking.save()

    messages.success(request, "Booking cancelled successfully.")

    return redirect('my_bookings')

# new admin
def is_admin(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_admin, login_url='/login/')
def admin_dashboard(request):
    time_filter = request.GET.get('filter', 'month')

    if request.user.is_superuser:
        my_hotels = Hotel.objects.all()
        my_rooms = Room.objects.all()
        all_bookings = Booking.objects.all()
        total_users = User.objects.count()
    else:
        my_hotels = Hotel.objects.filter(owner=request.user)
        my_rooms = Room.objects.filter(hotel__in=my_hotels)
        all_bookings = Booking.objects.filter(room__hotel__in=my_hotels)
        total_users = User.objects.filter(booking__room__hotel__in=my_hotels).distinct().count()

    confirmed_qs = all_bookings.filter(status='confirmed')
    cancelled_qs = all_bookings.filter(status='cancelled')

    total_bookings = all_bookings.count()
    confirmed_count = confirmed_qs.count()
    cancelled_count = cancelled_qs.count()
    total_hotels = my_hotels.count()
    total_rooms = my_rooms.count()
    total_revenue = confirmed_qs.aggregate(Sum('total_price'))['total_price__sum'] or 0

    recent_bookings = all_bookings.select_related('user', 'room', 'room__hotel').order_by('-id')[:7]

    now = timezone.now()
    trend_labels = []
    trend_revenue = []
    trend_bookings = []

    if time_filter == 'year':
        years = [now.year - 2, now.year - 1, now.year]
        for y in years:
            trend_labels.append(str(y))
            y_bookings = confirmed_qs.filter(check_in__year=y)
            rev = y_bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0
            cnt = all_bookings.filter(check_in__year=y).count()
            trend_revenue.append(float(rev))
            trend_bookings.append(cnt)
    else:
        for i in range(5, -1, -1):
            target_date = now - timedelta(days=i*30)
            m_label = target_date.strftime('%b %Y')
            m_year = target_date.year
            m_month = target_date.month

            trend_labels.append(m_label)
            m_bks = confirmed_qs.filter(check_in__year=m_year, check_in__month=m_month)
            rev = m_bks.aggregate(Sum('total_price'))['total_price__sum'] or 0
            cnt = all_bookings.filter(check_in__year=m_year, check_in__month=m_month).count()
            trend_revenue.append(float(rev))
            trend_bookings.append(cnt)

    room_types = ["Single", "Double", "Deluxe", "Suite"]
    room_type_revenue = []
    for rt in room_types:
        rt_rev = confirmed_qs.filter(room__room_type=rt).aggregate(Sum('total_price'))['total_price__sum'] or 0
        room_type_revenue.append(float(rt_rev))

    context = {
        'time_filter': time_filter,
        'total_revenue': round(total_revenue, 2),
        'total_bookings': total_bookings,
        'confirmed_count': confirmed_count,
        'cancelled_count': cancelled_count,
        'total_hotels': total_hotels,
        'total_rooms': total_rooms,
        'total_users': total_users,
        'recent_bookings': recent_bookings,
        'trend_labels_json': json.dumps(trend_labels),
        'trend_revenue_json': json.dumps(trend_revenue),
        'trend_bookings_json': json.dumps(trend_bookings),
        'status_labels_json': json.dumps(["Confirmed", "Cancelled"]),
        'status_counts_json': json.dumps([confirmed_count, cancelled_count]),
        'room_types_json': json.dumps(room_types),
        'room_type_revenue_json': json.dumps(room_type_revenue),
    }

    return render(request, 'bookings/admin_dashboard.html', context)
@user_passes_test(is_admin, login_url='/login/')
def admin_hotels(request):

    if request.user.is_superuser:

        hotels = Hotel.objects.all().order_by('-id')

    else:

        hotels = Hotel.objects.filter(
            owner=request.user
        ).order_by('-id')

    return render(
        request,
        'bookings/admin_hotels.html',
        {
            'hotels': hotels
        }
    )
@user_passes_test(is_admin, login_url='/login/')
def admin_add_hotel(request):

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')

        if name and address and city:

            Hotel.objects.create(
                    owner=request.user,
                    name=name,
                    address=address,
                    city=city,
                    description=description,
                    image=image
                )

            return redirect('admin_hotels')

    return render(
        request,
        'bookings/admin_add_hotel.html'
    )
@user_passes_test(is_admin, login_url='/login/')
def admin_edit_hotel(request, hotel_id):

    if request.user.is_superuser:

     hotel = get_object_or_404(
        Hotel,
        id=hotel_id
    )

    else:

     hotel = get_object_or_404(
        Hotel,
        id=hotel_id,
        owner=request.user
    )

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        description = request.POST.get('description', '').strip()

        if name and address and city:

            hotel.name = name
            hotel.address = address
            hotel.city = city
            hotel.description = description

            # Only replace image if a new image was uploaded
            new_image = request.FILES.get('image')

            if new_image:
                hotel.image = new_image

            hotel.save()

            return redirect('admin_hotels')

    return render(
        request,
        'bookings/admin_edit_hotel.html',
        {
            'hotel': hotel
        }
    )
@user_passes_test(is_admin, login_url='/login/')
def admin_delete_hotel(request, hotel_id):

    if request.method != 'POST':
        return redirect('admin_hotels')

    if request.user.is_superuser:

        hotel = get_object_or_404(
            Hotel,
            id=hotel_id
        )

    else:

        hotel = get_object_or_404(
            Hotel,
            id=hotel_id,
            owner=request.user
        )

    if Room.objects.filter(hotel=hotel).exists():

        messages.error(
            request,
            f'Cannot delete "{hotel.name}" because it has rooms associated with it.'
        )

        return redirect('admin_hotels')

    hotel_name = hotel.name

    hotel.delete()

    messages.success(
        request,
        f'Hotel "{hotel_name}" was deleted successfully.'
    )

    return redirect('admin_hotels')
@user_passes_test(is_admin, login_url='/login/')
def admin_rooms(request):

    # SUPER ADMIN
    # Can see all rooms
    if request.user.is_superuser:

        rooms = Room.objects.select_related(
            'hotel'
        ).order_by('-id')

    # HOTEL ADMIN
    # Can see only rooms belonging to their hotels
    else:

        rooms = Room.objects.filter(
            hotel__owner=request.user
        ).select_related(
            'hotel'
        ).order_by('-id')

    return render(
        request,
        'bookings/admin_rooms.html',
        {
            'rooms': rooms
        }
    )
@user_passes_test(is_admin, login_url='/login/')
def admin_add_room(request):

    # Hotels available to this admin
    if request.user.is_superuser:
        hotels = Hotel.objects.all()
    else:
        hotels = Hotel.objects.filter(owner=request.user)

    if request.method == 'POST':

        hotel_id = request.POST.get('hotel')
        room_number = request.POST.get('room_number')
        room_type = request.POST.get('room_type')
        capacity = request.POST.get('capacity')
        price_per_night = request.POST.get('price_per_night')
        description = request.POST.get('description')
        is_ac = request.POST.get('is_ac') in ['on', 'true', '1']
        has_wifi = request.POST.get('has_wifi') in ['on', 'true', '1']
        has_breakfast = request.POST.get('has_breakfast') in ['on', 'true', '1']

        # Get multiple uploaded images
        images = request.FILES.getlist('images')

        # Make sure the selected hotel belongs to this admin
        if request.user.is_superuser:
            hotel = get_object_or_404(Hotel, id=hotel_id)
        else:
            hotel = get_object_or_404(Hotel, id=hotel_id, owner=request.user)

        # Create the room
        room = Room.objects.create(
            hotel=hotel,
            room_number=room_number,
            room_type=room_type,
            capacity=capacity,
            price_per_night=price_per_night,
            description=description,
            is_ac=is_ac,
            has_wifi=has_wifi,
            has_breakfast=has_breakfast
        )

        # Save all room images
        for image in images:
            RoomImage.objects.create(room=room, image=image)

        messages.success(request, "Room and images added successfully!")
        return redirect('admin_rooms')

    return render(request, 'bookings/admin_add_room.html', {'hotels': hotels})


@user_passes_test(is_admin, login_url='/login/')
def admin_edit_room(request, room_id):
    if request.user.is_superuser:
        room = get_object_or_404(Room, id=room_id)
        hotels = Hotel.objects.all()
    else:
        room = get_object_or_404(Room, id=room_id, hotel__owner=request.user)
        hotels = Hotel.objects.filter(owner=request.user)

    if request.method == 'POST':
        hotel_id = request.POST.get('hotel')
        room_number = request.POST.get('room_number')
        room_type = request.POST.get('room_type')
        capacity = request.POST.get('capacity')
        price_per_night = request.POST.get('price_per_night')
        description = request.POST.get('description')
        is_ac = request.POST.get('is_ac') in ['on', 'true', '1']
        has_wifi = request.POST.get('has_wifi') in ['on', 'true', '1']
        has_breakfast = request.POST.get('has_breakfast') in ['on', 'true', '1']

        if request.user.is_superuser:
            hotel = get_object_or_404(Hotel, id=hotel_id)
        else:
            hotel = get_object_or_404(Hotel, id=hotel_id, owner=request.user)

        room.hotel = hotel
        room.room_number = room_number
        room.room_type = room_type
        room.capacity = capacity
        room.price_per_night = price_per_night
        room.description = description
        room.is_ac = is_ac
        room.has_wifi = has_wifi
        room.has_breakfast = has_breakfast

        room.save()

        # Handle image deletions
        delete_ids = request.POST.getlist('delete_images')
        if delete_ids:
            RoomImage.objects.filter(id__in=delete_ids, room=room).delete()

        # Handle new image uploads
        new_images = request.FILES.getlist('images')
        for img in new_images:
            RoomImage.objects.create(room=room, image=img)

        messages.success(request, "Room updated successfully!")
        return redirect('admin_rooms')

    return render(
        request,
        'bookings/admin_edit_room.html',
        {
            'room': room,
            'hotels': hotels
        }
    )
@user_passes_test(is_admin, login_url='/login/')
def admin_delete_room(request, room_id):

    if request.method != 'POST':
        return redirect('admin_rooms')

    # Super Admin
    if request.user.is_superuser:

        room = get_object_or_404(
            Room,
            id=room_id
        )

    # Hotel Admin
    else:

        room = get_object_or_404(
            Room,
            id=room_id,
            hotel__owner=request.user
        )

    room_name = room.room_number

    # Don't delete a room that has bookings
    if Booking.objects.filter(room=room).exists():

        messages.error(
            request,
            f"Room {room_name} cannot be deleted because it has bookings."
        )

        return redirect('admin_rooms')

    room.delete()

    messages.success(
        request,
        f"Room {room_name} deleted successfully!"
    )

    return redirect('admin_rooms')