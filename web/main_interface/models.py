from django.db import models
from django.utils import timezone
import uuid


class TelegramToken(models.Model):
    """Модель для хранения токенов авторизации через Telegram"""

    EXPIRATION_MINUTES = 30  # Увеличено с 15 до 30 минут

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
        """Проверить, истек ли токен"""
        if self.status in ["used", "expired"]:
            return True
        # Обработанные токены не истекают по времени - они должны быть использованы
        if self.status == "processed":
            return False

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
            # Если токен уже обработан или использован, возвращаем его независимо от времени
            if telegram_token.status in ["processed", "used"]:
                return telegram_token
            # Для pending токенов проверяем истечение
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


class PhoneAuthCode(models.Model):
    """Модель для хранения кодов авторизации по номеру телефона"""

    EXPIRATION_MINUTES = 5
    CODE_LENGTH = 6

    STATUS_CHOICES = [
        ("pending", "Ожидает подтверждения"),
        ("verified", "Подтвержден"),
        ("expired", "Истек"),
    ]

    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=10)
    telegram_user_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Phone Auth Code"
        verbose_name_plural = "Phone Auth Codes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone", "status"]),
        ]

    def __str__(self):
        return f"{self.phone} - {self.status}"

    def mark_verified(self, telegram_user_id):
        """Отметить код как подтвержденный"""
        self.telegram_user_id = telegram_user_id
        self.status = "verified"
        self.verified_at = timezone.now()
        self.save()

    def mark_expired(self):
        """Отметить код как истекший"""
        if self.status != "expired":
            self.status = "expired"
            self.save(update_fields=["status"])

    def increment_attempts(self):
        """Увеличить счетчик попыток"""
        self.attempts += 1
        self.save(update_fields=["attempts"])

    def is_expired(self):
        """Проверить, истек ли код"""
        if self.status in ["verified", "expired"]:
            return True

        from datetime import timedelta
        expiration_time = self.created_at + timedelta(minutes=self.EXPIRATION_MINUTES)
        return timezone.now() > expiration_time

    def is_max_attempts_reached(self):
        """Проверить, достигнут ли лимит попыток"""
        return self.attempts >= self.max_attempts

    @classmethod
    def create_code(cls, phone):
        """Создать новый код для номера телефона"""
        import random
        import string
        
        # Истекаем все предыдущие коды для этого номера
        cls.objects.filter(phone=phone, status="pending").update(status="expired")
        
        # Генерируем 6-значный код
        code = ''.join(random.choices(string.digits, k=cls.CODE_LENGTH))
        
        return cls.objects.create(phone=phone, code=code)

    @classmethod
    def get_valid_code(cls, phone, code):
        """Получить валидный код"""
        try:
            auth_code = cls.objects.filter(
                phone=phone,
                code=code,
                status="pending"
            ).order_by("-created_at").first()
            
            if not auth_code:
                return None
                
            if auth_code.is_expired():
                auth_code.mark_expired()
                return None
                
            if auth_code.is_max_attempts_reached():
                auth_code.mark_expired()
                return None
                
            return auth_code
        except Exception:
            return None
