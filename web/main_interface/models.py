from django.db import models
from django.utils import timezone
import uuid


class TelegramToken(models.Model):
    """Модель для хранения токенов авторизации через Telegram"""

    EXPIRATION_MINUTES = 15

    STATUS_CHOICES = [
        ("pending", "Ожидает обработки"),
        ("processed", "Обработан ботом"),
        ("used", "Использован для авторизации"),
        ("expired", "Истек"),
    ]

    token = models.CharField(max_length=100, unique=True, db_index=True)
    telegram_user_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Telegram Token"
        verbose_name_plural = "Telegram Tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.token} - {self.status}"

    def mark_processed(self, telegram_user_id):
        """Отметить токен как обработанный ботом"""
        self.telegram_user_id = telegram_user_id
        self.status = "processed"
        self.processed_at = timezone.now()
        self.save()

    def mark_used(self):
        """Отметить токен как использованный"""
        self.status = "used"
        self.used_at = timezone.now()
        self.save()

    def mark_expired(self):
        """Отметить токен как истекший"""
        if self.status != "expired":
            self.status = "expired"
            self.save(update_fields=["status"])

    def is_expired(self):
        """Проверить, истек ли токен (например, через 10 минут)"""
        if self.status in ["used", "expired"]:
            return True

        # Токен истекает через EXPIRATION_MINUTES минут после создания
        from datetime import timedelta

        expiration_time = self.created_at + timedelta(minutes=self.EXPIRATION_MINUTES)
        return timezone.now() > expiration_time

    @classmethod
    def create_token(cls):
        """Создать новый токен"""
        token = f"telegram_{uuid.uuid4()}"
        return cls.objects.create(token=token)

    @classmethod
    def get_valid_token(cls, token):
        """Получить валидный токен"""
        try:
            telegram_token = cls.objects.get(token=token)
            if telegram_token.is_expired():
                telegram_token.status = "expired"
                telegram_token.save(update_fields=["status"])
                return None
            return telegram_token
        except cls.DoesNotExist:
            return None

    @classmethod
    def expire_token(cls, token):
        """Принудительно истечь токен (например, при повторной выдаче)"""
        try:
            telegram_token = cls.objects.get(token=token)
            telegram_token.mark_expired()
        except cls.DoesNotExist:
            return
