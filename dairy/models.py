from django.db import models
from datetime import date
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class Breed(models.Model):
    """Stores information about the breed"""
    Friesian, Ayshire, Jersey, Guernsey = "Friesian", "Ayshire", "Jersey", "Guernsey"
    Breed_choices = ((Friesian, "Friesian"), (Ayshire, "Ayshire"), (Jersey, "Jersey"), (Guernsey, "Guernsey"))
    names = models.CharField(max_length=32, choices=Breed_choices)

    def __str__(self):
        return self.names.capitalize()


class Cow(models.Model):
    """Stores information about the cow"""
    STATUS_CHOICES = (('A', 'Alive'), ('D', 'Dead'), ('S', 'Sold'))
    PREGNANCY_STATUS = (('P', 'Pregnant'), ('C', 'Calved'), ('N', 'Not pregnant'))

    name = models.CharField(max_length=64, blank=True, null=True)
    breed = models.ForeignKey(Breed, on_delete=models.PROTECT, related_name='breed')
    date_of_birth = models.DateField(validators=[MaxValueValidator(date.today())])
    sire = models.ForeignKey('self', on_delete=models.PROTECT, related_name='offspring', blank=True, null=True)
    dam = models.ForeignKey('self', on_delete=models.PROTECT, related_name='calves', blank=True, null=True)
    calf = models.ForeignKey('self', on_delete=models.PROTECT, related_name='calf_of', blank=True, null=True)  # Changed related_name
    gender = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female')), db_index=True)
    availability_status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    pregnancy_status = models.CharField(max_length=1, choices=PREGNANCY_STATUS, default='N')
    date_of_death = models.DateField(validators=[MaxValueValidator(date.today())], blank=True, null=True)

    @property
    def tag_number(self):
        year_of_birth = self.date_of_birth.strftime('%y')
        first_two_letters_of_breed = self.breed.names[:2].upper()
        counter = self.id
        return f'{first_two_letters_of_breed}-{year_of_birth}-{counter}'

    @property
    def parity(self):
        return self.calves.count()

    @property
    def age(self):
        age_in_days = self.get_cow_age()
        if age_in_days < 30:
            weeks = int(age_in_days / 7)
            days = age_in_days % 7
            return f"{weeks}wk, {days}d"
        elif age_in_days < 365:
            months = int(age_in_days / 30)
            weeks = int((age_in_days % 30) / 7)
            return f"{months}m, {weeks}wk"
        else:
            years = int(age_in_days / 365)
            months = int((age_in_days % 365) / 30)
            return f"{years}y, {months}m"

    def get_cow_age(self):
        return (timezone.now().date() - self.date_of_birth).days

    def clean(self):
        cow_age = self.get_cow_age() / 365
        if cow_age > 7:
            raise ValidationError('Cow cannot be older than 7 years!')

        if self.availability_status == 'D':
            if not self.date_of_death:
                raise ValidationError("Sorry, this cow died! Update its status by adding the date of death.")
            if (timezone.now().date() - self.date_of_death).days > 1:
                raise ValidationError("Date of death longer than 24 hours ago is not allowed.")

        if (self.get_cow_age() / 30) < 21 and self.pregnancy_status == 'P':
            raise ValidationError({'pregnancy_status': "Cows must be 21 months or older to be set as pregnant."})

        if self.get_cow_age() / 30 < 21 and self.calf is not None:
            raise ValidationError("This cow is still young and cannot have a calf")

        if self.availability_status == 'D' and self.pregnancy_status != 'N':
            raise ValidationError({'pregnancy_status': 'Dead cows can only have a "not pregnant" status'})

    def __str__(self):
        return self.name


class Milk(models.Model):
    """Stores information about the milk production"""
    MILKING_TIMES = ((1, "Morning"), (2, "Afternoon"), (3, "Evening"), (4, "Night"))

    milking_time_value = models.IntegerField(editable=False, choices=MILKING_TIMES)
    milking_date = models.DateTimeField(auto_now_add=True)
    cow = models.ForeignKey(Cow, on_delete=models.CASCADE, related_name='milk')
    amount_in_kgs = models.DecimalField(
        verbose_name="Amount (kg)",
        default=0.00,
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0, message="Amount of milk cannot be less than 0 kgs!"),
            MaxValueValidator(35, message="Amount of milk cannot be more than 35 kgs!")
        ]
    )

    class Meta:
        verbose_name_plural = "Milk"
        unique_together = ('cow', 'milking_time_value')

    @property
    def milking_time(self):
        return self.get_milking_time_value_display()

    def set_milking_time(self):
        hour = self.milking_date.hour
        if 3 <= hour < 8:
            self.milking_time_value = 1
        elif 8 <= hour < 13:
            self.milking_time_value = 2
        elif 13 <= hour < 18:
            self.milking_time_value = 3
        else:
            self.milking_time_value = 4

    def __str__(self):
        return f"Milk record of cow {self.cow.name} at {self.milking_time} on {self.milking_date.strftime('%y-%d-%m %H:%M:%S')}"

    def clean(self):
        cow = self.cow
        cow_age = cow.get_cow_age()
        if cow.availability_status == "D":
            raise ValidationError("Cannot add milk record for a dead cow!")
        if cow.availability_status == "S":
            raise ValidationError("Cannot add milk record for a sold cow!")
        if cow_age < 21 * 30:
            raise ValidationError("Cannot add milk record for a cow less than 21 months!")

        if self.milking_date is None:
            self.milking_date = timezone.now()
        try:
            existing_milk_record = Milk.objects.get(
                cow=self.cow,
                milking_date__date=self.milking_date.date(),
                milking_time_value=self.milking_time_value
            )
            if existing_milk_record and not self.pk:
                raise ValidationError("A milk record already exists for this cow at this milking time.")
        except Milk.DoesNotExist:
            pass

        if cow.gender != "F":
            raise ValidationError("This cow is male and cannot produce milk!")

        self.set_milking_time()
        if not self.milking_date:
            self.milking_date = timezone.now()
        if self.amount_in_kgs <= 0:
            raise ValidationError("Amount in kgs should be greater than 0")


