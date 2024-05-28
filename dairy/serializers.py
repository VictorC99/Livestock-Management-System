from rest_framework import serializers

from .models import *


class CowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cow
        fields = "__all__"


class CowSerializer(serializers.ModelSerializer):
    breed = CowSerializer()
    tag_number = serializers.ReadOnlyField()
    parity = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    age_in_farm = serializers.ReadOnlyField()

    class Meta:
        model = Cow
        fields = "__all__"

    def create(self, validated_data):
        breed_data = validated_data.pop("breed")
        breed, _ = Breed.objects.get_or_create(**breed_data)

        cow = Cow.objects.create(breed=breed, **validated_data)
        return cow

    def update(self, instance, validated_data):
        fields_to_exclude = [
            "breed",
            "gender",
            "sire",
            "dam",
            "is_bought",
            "date_introduced_in_farm",
        ]
        for field in fields_to_exclude:
            validated_data.pop(field, None)
        return super().update(instance, validated_data)


class HeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Heat
        fields = "__all__"

class PregnancySerializer(serializers.ModelSerializer):
    due_date = serializers.ReadOnlyField()
    pregnancy_duration = serializers.ReadOnlyField()

    class Meta:
        model = Pregnancy
        fields = "__all__"


class LactationSerializer(serializers.ModelSerializer):
    days_in_lactation = serializers.ReadOnlyField()
    lactation_stage = serializers.ReadOnlyField()
    end_date_ = serializers.ReadOnlyField()

    class Meta:
        model = Lactation
        fields = "__all__"

    def create(self, validated_data):
        # Get the cow instance from the validated data
        cow_instance = validated_data["cow"]

        LactationValidator.validate_cow_origin(cow_instance)
        LactationValidator.validate_cow_category(cow_instance.category)

        lactation_instance = Lactation.objects.create(**validated_data)
        return lactation_instance


class MilkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milk
        fields = "__all__"


