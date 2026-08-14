from django.contrib import admin
from .models import Hotel, Room, Booking, RoomImage


# -----------------------------
# ROOM IMAGE INLINE
# -----------------------------
class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 3


# -----------------------------
# HOTEL ADMIN
# -----------------------------
@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "address")
    search_fields = ("name", "city")


# -----------------------------
# ROOM ADMIN
# -----------------------------
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "hotel", "room_type", "price_per_night")
    list_filter = ("hotel", "room_type")
    inlines = [RoomImageInline]   # ✅ ADD HERE


# -----------------------------
# BOOKING ADMIN
# -----------------------------
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("user", "room", "check_in", "check_out", "guests")
    list_filter = ("check_in", "room__hotel")

