import copy
from rest_framework.serializers import ModelSerializer

from .models import Carrier, Shipment, Insurance, ShipmentItem


class CarrierSerializer(ModelSerializer):
    class Meta:
        fields = ('name', 'phone')
        model = Carrier


class InsuranceSerializer(ModelSerializer):
    class Meta:
        model = Insurance
        fields = ('company_name', 'cost')


class ShipmentItemSerializer(ModelSerializer):
    class Meta:
        model = ShipmentItem
        fields = ('name', 'quantity')


class ShipmentSerializer(ModelSerializer):
    # The insurance data does not follow this way.
    carrier = CarrierSerializer(required=False)
    shipmentitem_set = ShipmentItemSerializer(many=True, required=True)

    class Meta:
        model = Shipment
        fields = ('shipment_no', 'first_name', 'last_name', 'email', 'address', 'city', 'state', 'zipcode',
                  'country', 'phone', 'shipmentitem_set', 'carrier', 'carrier_quote', 'need_insurance',
                  'carrier_quote', 'post_label')

    def create(self, validated_data):
        items_data = validated_data.pop('shipmentitem_set')
        validated_data.pop('owner', None)  # injected previously.
        shipment = Shipment.objects.create(**validated_data)
        for item_data in items_data:
            ShipmentItem.objects.create(shipment=shipment, **item_data)
        return shipment

    def update(self, instance, validated_data):
        # This is required for doing nested write.
        carrier_data = validated_data.pop('carrier', None)
        data = copy.copy(validated_data)
        if carrier_data:
            carrier = Carrier.objects.get(**carrier_data)
            data['carrier'] = carrier
        for attr, value in data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
