from rest_framework import serializers


class PaymentSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=8, help_text="Номер карты (8 цифр)")
    name = serializers.CharField(max_length=100, help_text="Имя владельца")
    month = serializers.IntegerField(min_value=1, max_value=12, help_text="Месяц (1-12)")
    year = serializers.IntegerField(min_value=2024, max_value=2034, help_text="Год")
    code = serializers.CharField(max_length=3, min_length=3, help_text="CVV код")

    def validate_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Номер карты должен содержать только цифры")
        if int(value) % 2 != 0:
            raise serializers.ValidationError("Номер карты должен быть чётным")
        return value

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("CVV должен содержать только цифры")
        return value
