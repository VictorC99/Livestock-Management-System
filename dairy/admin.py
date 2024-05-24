from django.contrib import admin
from .models import Breed
from .models import Cow
from .models import Milk
from .models import Heat
from .models import Pregnancy
from .models import Lactation

# Register your models here.

admin.site.register(Breed)
admin.site.register(Cow)
admin.site.register(Milk)
admin.site.register(Heat)
admin.site.register(Pregnancy)
admin.site.register(Lactation)
