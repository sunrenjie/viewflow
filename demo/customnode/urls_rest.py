from viewflow.flow.viewset_rest import FlowViewSet
from .flows import DynamicSplitFlow


urlpatterns = FlowViewSet(DynamicSplitFlow).urls
