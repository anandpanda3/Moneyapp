from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone

class Category(models.Model):
    CATEGORY_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    class Meta:
        verbose_name_plural = "Categories"


class Transaction(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.category and self.category.type == 'expense' and self.amount > 0:
            self.amount = -self.amount
        super().save(*args, **kwargs)

    @property
    def transaction_type(self):
        return 'income' if self.amount >= 0 else 'expense'

    def __str__(self):
        return f"{self.amount} - {self.category} - {self.date}"


class Budget(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # Если категория не указана, использовать категорию "Общий" как дефолтную
        if not self.category:
            self.category = Category.objects.get_or_create(name="Общий", defaults={'type': 'expense'})[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category} - {self.amount}"

    def remaining_budget(self):
        current_date = timezone.now().date()
        if current_date < self.start_date or current_date > self.end_date:
            return 0
        
        # Для бюджета с категорией "Общий" нужно учитывать все транзакции, и доходы и расходы
        if self.category.name == "Общий":
            spent = Transaction.objects.filter(
                user=self.user,
                date__range=(self.start_date, self.end_date)
            ).aggregate(Sum('amount'))['amount__sum'] or 0
        else:
            spent = Transaction.objects.filter(
                user=self.user,
                category=self.category,
                date__range=(self.start_date, self.end_date)
            ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        return self.amount + spent  # Расходы будут отрицательными, а доходы положительными


class TotalBudget(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Total Budget: {self.amount}"

    def total_remaining_budget(self):
        current_date = timezone.now().date()
        if current_date < self.start_date or current_date > self.end_date:
            return 0
        spent = Transaction.objects.filter(
            user=self.user,
            date__range=(self.start_date, self.end_date)
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        return self.amount + spent  # spent is negative for expenses


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    notifications_enabled = models.BooleanField(default=False)
    dark_mode = models.BooleanField(default=True)
    language = models.CharField(max_length=2, default='ru', choices=[('ru', 'Russian'), ('en', 'English')])

    def __str__(self):
        return f"{self.user.username}'s settings"
