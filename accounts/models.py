from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# Create your models here.
class Profile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )


    #---- PERSONAL INFO ----
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to = 'avatars/', blank=True, null = True, default = 'avatars/default.png')
    bio = models.TextField(blank=True, max_length=500)

    # Default shipping address
    # useful so checkout can pre-fill these fields.
    address = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)


    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s profile"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def has_address(self):
        return all([self.address, self.city, self.postal_code, self.country])




# For auto crerate / auto-save profile
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):

    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)