from viewflow.flow.viewset_rest import FlowViewSet
from .flows import OrderItCompleteProjectFlow

urlpatterns = FlowViewSet(OrderItCompleteProjectFlow).urls
