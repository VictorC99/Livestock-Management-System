from django.db import models
from datetime import date
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from dairy.managers import *
from dairy.validators import *

# Create your models here.

class Breed(models.Model):
    """Stores information about the breed"""
    Friesian, Ayshire, Jersey, Guernsey = "Friesian", "Ayshire", "Jersey", "Guernsey"
    Breed_choices = ((Friesian, "Friesian"), (Ayshire, "Ayshire"), (Jersey, "Jersey"), (Guernsey, "Guernsey"))
    name = models.CharField(max_length=32, choices=Breed_choices)

    def __str__(self):
        return self.name.capitalize()


class Cow(models.Model):
    """Stores information about the cow"""
    STATUS_CHOICES = (('A', 'Alive'), ('D', 'Dead'), ('S', 'Sold'))
    PREGNANCY_STATUS = (('P', 'Pregnant'), ('C', 'Calved'), ('N', 'Not pregnant'))

    name = models.CharField(max_length=64, blank=True, null=True)
    breed = models.ForeignKey(Breed, on_delete=models.PROTECT, related_name='cows')
    date_of_birth = models.DateField(validators=[MaxValueValidator(date.today())])
    sire = models.ForeignKey('self', on_delete=models.PROTECT, related_name='offspring', blank=True, null=True)
    dam = models.ForeignKey('self', on_delete=models.PROTECT, related_name='calves', blank=True, null=True)
    calf = models.ForeignKey('self', on_delete=models.PROTECT, related_name='calf_of', blank=True, null=True)
    gender = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female')), db_index=True)
    availability_status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    pregnancy_status = models.CharField(max_length=1, choices=PREGNANCY_STATUS, default='N')
    date_of_death = models.DateField(validators=[MaxValueValidator(date.today())], blank=True, null=True)

    @property
    def tag_number(self):
        year_of_birth = self.date_of_birth.strftime('%y')
        first_two_letters_of_breed = self.breed.name[:2].upper()
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
    class Meta:
        verbose_name_plural = "Milk"
        unique_together = ('cow', 'milking_date', 'milking_time_value')

    MILKING_TIMES = ((1, "Morning"), (2, "Afternoon"), (3, "Evening"), (4, "Night"))
    milking_time_value = models.IntegerField(editable=False, choices=MILKING_TIMES)
    milking_date = models.DateTimeField(auto_now_add=True)
    cow = models.ForeignKey(Cow, on_delete=models.CASCADE, related_name='milk')
    amount_in_kgs = models.DecimalField(verbose_name="Amount (kg)", default=0.00, max_digits=5, decimal_places=2, blank=True, null=True,
                                        validators=[MinValueValidator(0, message="Amount of milk cannot be less than 0 kgs!"),
                                                    MaxValueValidator(35, message="Amount of milk cannot be more than 35 kgs!")])

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
            existing_milk_record = Milk.objects.get(cow=self.cow, milking_date__date=self.milking_date.date(), milking_time_value=self.milking_time_value)
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

class Heat(models.Model):
    """
    Represents a record of heat observation in a cow.
    """
    observation_time = models.DateTimeField()
    cow = models.ForeignKey(Cow, on_delete=models.CASCADE, related_name="heat_records")

    def __str__(self):
        return f"Heat record for cow {self.cow.tag_number} on {self.observation_time}"

    def clean(self):
        super().clean()
        HeatValidator.validate_observation_time(self.observation_time)
        HeatValidator.validate_pregnancy(self.cow)
        HeatValidator.validate_production_status(self.cow)
        HeatValidator.validate_dead(self.cow)
        HeatValidator.validate_gender(self.cow)
        HeatValidator.validate_within_60_days_after_calving(self.cow, self.observation_time)
        HeatValidator.validate_within_21_days_of_previous_heat(self.cow, self.observation_time)
        HeatValidator.validate_min_age(self.cow)
        HeatValidator.validate_already_in_heat(self.cow)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class Pregnancy(models.Model):
    """
    Represents a pregnancy record for a cow.
    """
    cow = models.ForeignKey(Cow, on_delete=models.PROTECT, related_name="pregnancies")
    start_date = models.DateField()
    date_of_calving = models.DateField(null=True, blank=True)
    pregnancy_status = models.CharField(
        max_length=11,
        choices=PregnancyStatusChoices.choices,
        default=PregnancyStatusChoices.UNCONFIRMED,
    )
    pregnancy_notes = models.TextField(blank=True)
    calving_notes = models.TextField(blank=True)
    pregnancy_scan_date = models.DateField(null=True, blank=True)
    pregnancy_failed_date = models.DateField(null=True, blank=True)
    pregnancy_outcome = models.CharField(
        max_length=11, choices=PregnancyOutcomeChoices.choices, blank=True, null=True
    )

    objects = models.Manager()
    manager = PregnancyManager()

    @property
    def pregnancy_duration(self):
        return PregnancyManager.pregnancy_duration(self)

    @property
    def latest_lactation_stage(self):
        return PregnancyManager.latest_lactation_stage(self)

    def clean(self):
        super().clean()
        PregnancyValidator.validate_age(self.cow.age, self.start_date, self.cow)
        PregnancyValidator.validate_cow_current_pregnancy_status(self.cow)
        PregnancyValidator.validate_cow_availability_status(self.cow)
        PregnancyValidator.validate_dates(
            self.start_date,
            self.pregnancy_status,
            self.date_of_calving,
            self.pregnancy_scan_date,
            self.pregnancy_failed_date,
        )
        PregnancyValidator.validate_pregnancy_status(
            self.pregnancy_status, self.start_date, self.pregnancy_failed_date
        )
        PregnancyValidator.validate_outcome(
            self.pregnancy_outcome, self.pregnancy_status, self.date_of_calving
        )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Lactation(models.Model):
    """
    Represents a lactation period for a cow.
    """
    class Meta:
        get_latest_by = "-start_date"

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    cow = models.ForeignKey(Cow, on_delete=models.CASCADE, related_name="lactations")
    lactation_number = models.PositiveSmallIntegerField(default=1)
    pregnancy = models.OneToOneField(Pregnancy, on_delete=models.CASCADE, null=True, blank=True)

    objects = models.Manager()
    manager = LactationManager()

    @property
    def days_in_lactation(self):
        return self.manager.days_in_lactation(self)

    @property
    def lactation_stage(self):
        return self.manager.lactation_stage(self)

    @property
    def end_date_(self):
        return self.manager.lactation_end_date(self)

    def __str__(self):
        return f"Lactation record {self.lactation_number} for {self.cow}"

    def clean(self):
        super().clean()
        LactationValidator.validate_age(self.start_date, self.cow)
        LactationValidator.validate_fields(
            self.start_date, self.pregnancy, self.lactation_number, self.cow, self
        )
        # LactationValidator.validate_cow_category(self.cow.category)
        # LactationValidator.validate_cow_origin(self.cow)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
 