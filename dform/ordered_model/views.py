# ordered_model.views.py
import logging

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

from common.decorators import staff_required

logger = logging.getLogger(__name__)

# =============================================================================
# Admin Views
# =============================================================================

@staff_required
def ordered_item_up(request, content_type_id, item_id):
    content_type = ContentType.objects.get_for_id(content_type_id)
    item = get_object_or_404(content_type.model_class(), id=item_id)
    item.order -= 1
    item.save()

    return HttpResponseRedirect(request.META['HTTP_REFERER'])


@staff_required
def ordered_item_down(request, content_type_id, item_id):
    content_type = ContentType.objects.get_for_id(content_type_id)
    item = get_object_or_404(content_type.model_class(), id=item_id)
    item.order += 1
    item.save()

    return HttpResponseRedirect(request.META['HTTP_REFERER'])
