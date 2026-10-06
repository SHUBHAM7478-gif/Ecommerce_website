from django.db import models
from django.urls import reverse
from django.utils.text import slugify


# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(max_length=500, blank=True)
    image = models.ImageField(
        upload_to = 'categories/',
        blank = True,
        null = True,
    )
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Catrgories'
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product_list") + f'?category={self.slug}'


    @property
    def product_count(self):
        return self.products.filter(available=True).count()



class Product(models.Model):
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null = True,
        blank=True,
        help_text = "Optional. Leave empty if not on sale. ",
    )
    stock = models.PositiveIntegerField(default = 0)


    image = models.ImageField(
        upload_to = 'products/',
        blank = True,
        null = True,
    )

    available = models.BooleanField(default = True)
    featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            n = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}---{n}"
                n+=1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:product_detail', kwargs={'slug': self.slug})  
    


    @property
    def is_on_sale(self):
        """True when discount_price is set and lower than price."""
        return (
            self.discount_price is not None
            and self.discount_price < self.price
        )


        
    @property
    def current_price(self):
        """Return the price the customer will actually pay."""
        return self.discount_price if self.is_on_sale else self.price

    @property
    def discount_percent(self):
        if not self.is_on_sale or self.price == 0:
            return 0
        diff = self.price - self.discount_price
        return int((diff / self.price) * 100)

    @property
    def in_stock(self):
        return self.stock > 0 and self.available


# ---------------------------------------------------------------------------
# PRODUCT IMAGE (gallery)
# ---------------------------------------------------------------------------
class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['created_at']

    def __str__(self):
        return f"Image for {self.product.name}"