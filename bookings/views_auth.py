from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import random
import time


# STEP 1: User enters email & password
def otp_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check if email exists
        users = User.objects.filter(email=email)
        if not users.exists():
            messages.error(request, "No account found with this email.")
            return redirect("otp_login")

        # Validate password against user account(s) matching this email
        user = None
        for u in users:
            if authenticate(username=u.username, password=password):
                user = u
                break

        if not user:
            messages.error(request, "Invalid password.")
            return redirect("otp_login")

        # Generate OTP
        otp = random.randint(100000, 999999)

        # Save OTP inside session
        request.session["otp"] = otp
        request.session["otp_user_id"] = user.id
        request.session["otp_expiry"] = time.time() + 300  # expires in 5 min

        # Send OTP email
        from .email_service import send_otp_email
        email_sent = send_otp_email(email, otp)
        if email_sent:
            messages.success(request, "OTP sent to your email.")
        else:
            messages.warning(request, f"OTP generated ({otp}), but sending the email failed. Please check mail service credentials.")

        return redirect("otp_verify")

    return render(request, "bookings/otp_login.html")


# STEP 2: Verify OTP
def otp_verify(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        otp = request.session.get("otp")
        otp_expiry = request.session.get("otp_expiry")
        user_id = request.session.get("otp_user_id")

        if not otp or not user_id:
            messages.error(request, "Session expired. Please login again.")
            return redirect("otp_login")

        # Check expiry
        if time.time() > otp_expiry:
            messages.error(request, "OTP expired. Please login again.")
            return redirect("otp_login")

        # Check OTP match
        if str(otp) != str(entered_otp):
            messages.error(request, "Incorrect OTP.")
            return redirect("otp_verify")

        # OTP correct → login
        user = User.objects.get(id=user_id)
        login(request, user)

        # Remove OTP from session
        for key in ["otp", "otp_expiry", "otp_user_id"]:
            if key in request.session:
                del request.session[key]

        messages.success(request, "Login successful!")
        return redirect("home")

    return render(request, "bookings/otp_verify.html")
