from .base import ComponentAdapter
from .element_ui_vue3 import ElementUIVue3Adapter
from .antd import AntDesignAdapter


def get_adapter(framework_name="element-ui-vue3", page=None):
    adapters = {
        "element-ui-vue3": ElementUIVue3Adapter(),
        "antd": AntDesignAdapter(page),
    }
    return adapters.get(framework_name, adapters["element-ui-vue3"])
