from viewflow.flow.viewset import FlowViewSet
from .flows import OrderItCompleteProjectFlow

urlpatterns = FlowViewSet(OrderItCompleteProjectFlow).urls
