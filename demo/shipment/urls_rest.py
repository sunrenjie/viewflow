from viewflow.flow.viewset_rest import FlowViewSet
from .flows import ShipmentFlow

urlpatterns = FlowViewSet(ShipmentFlow).urls
