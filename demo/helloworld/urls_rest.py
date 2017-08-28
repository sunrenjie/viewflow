from viewflow.flow.viewset_rest import FlowViewSet
from .flows import HelloWorldFlow


urlpatterns = FlowViewSet(HelloWorldFlow).urls
