from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date
from django.db.models.signals import post_save
from django.dispatch import receiver


# -------------------------------
# HOTEL MODEL
# -------------------------------
class Hotel(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_hotels'
    )

    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="hotels/", blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.exists():
            return round(sum(r.rating for r in ratings) / ratings.count(), 1)
        return 4.8

    @property
    def ratings_count(self):
        return self.ratings.count()


# -------------------------------
# ROOM MODEL
# -------------------------------
class Room(models.Model):
    ROOM_TYPES = [
        ("Single", "Single"),
        ("Double", "Double"),
        ("Deluxe", "Deluxe"),
        ("Suite", "Suite"),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    capacity = models.IntegerField(default=1)
    description = models.TextField(blank=True)
    
    # Amenities
    is_ac = models.BooleanField(default=True)
    has_wifi = models.BooleanField(default=True)
    has_breakfast = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "room_number"],
                name="unique_room_number_per_hotel"
            )
        ]

    def __str__(self):
        return f"{self.hotel.name} - Room {self.room_number}"


# -------------------------------
# HOTEL RATING / REVIEW MODEL
# -------------------------------
class HotelRating(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)  # 1 to 5 stars
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("hotel", "user")

    def __str__(self):
        return f"{self.user.username} rated {self.hotel.name}: {self.rating}★"


# -------------------------------
# BOOKING MODEL
# -------------------------------
class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    payment_status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Paid', 'Paid')],
        default='Pending'
    )

    status = models.CharField(
        max_length=20,
        choices=[('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')],
        default='confirmed'
    )

    def clean(self):
        if not self.room_id:
            return

        overlapping = Booking.objects.filter(
            room=self.room,
            status='confirmed',
            check_in__lt=self.check_out,
            check_out__gt=self.check_in,
        )

        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)

        if overlapping.exists():
            raise ValidationError("This room is already booked for these dates.")

    def save(self, *args, **kwargs):
        if self.check_in and self.check_out:
            days = (self.check_out - self.check_in).days
            if days > 0:
                self.total_price = self.room.price_per_night * days
            else:
                self.total_price = self.room.price_per_night

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking ID {self.id} - Room {self.room.room_number}"


# -------------------------------
# USER PROFILE MODEL
# -------------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', default='profiles/default.jpg')

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)


# -------------------------------
# ROOM IMAGE MODEL
# -------------------------------
class RoomImage(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='rooms/')

    def __str__(self):
        return f"Image for {self.room}"
