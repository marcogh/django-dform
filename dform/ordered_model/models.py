# ordered_model.models.py
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# =============================================================================

class OrderedModel(models.Model):
    """OrderedModel is an abstract class used to create a series of objects
    that have a numeric order in the database.  The value of the order is
    stored in the "order" field.  
    
    Groups of objects, each with their own ordering can be defined.  The 
    :func:`OrderedModel.ordered_filter` should return the subset of objects in
    the same group as the current object.  The default behavior is to return
    all objects of the same class.  If, for example, the child object had a
    "role" field where groupings where to be on that field, the 
    :func:`OrderedModel.ordered_filter` method should return
    `self.models.filter(role=self.role)`.

    The integrtiy of the "order" field is maintained by a signal, as such, the
    value of the field is not guaranteed to be what you save it as.  If you do
    not specify the field when constructing the child class, the object is put
    at the end of the ordered group.  If you do specify the value, then any
    items after the object will have their order incremented.  Values larger
    than the current number of objects in the list are ignored and set to the
    last item in the list.

    Methods and urls are provided for changing the position of an item within
    the django admin.  To use them, include the provided urls file in your url
    namespace and list the :func:`OrderedModel.admin_up_link` and
    :func:`OrderedModel.admin_down_link` methods in your "display_list"
    parameter of the admin class.

    An ORDERED_MODEL_CONFIG hash can be included in the settings to override
    certain the link values in the admin.

    *Example* ::
        ORDRED_MODEL_CONFIG = {
            'up_html':'UP',
            'down_html':'DOWN'
        }

    Config Fields::
        :up_html:
            Text to show in the anchor link in the admin for the up link
        :down_html:
            Text to show in the anchor link in the admin for the down link
    """
    order = models.PositiveSmallIntegerField(db_index=True)

    class Meta:
        abstract = True
        ordering = ['order']

    def __init__(self, *args, **kwargs):
        super(OrderedModel, self).__init__(*args, **kwargs)
        self._last_known_order = self.order

    def ordered_filter(self):
        """So that you can order a subset of objects (rather than the order
        being for the entire list) this method is called each time the model
        needs to manipulate the orders.  The default implementation is to
        return all objects of this type."""
        return self.__class__.objects.all()

    # ----------------------------------
    # Admin Link Methods

    def admin_up_link(self):
        if self.order == 1:
            return ''

        content_type = ContentType.objects.get_for_model(self)
        link = reverse('ordered_model.views.ordered_item_up',
            args=(content_type.id, self.id))
        text = 'up'
        if hasattr(settings, 'ORDERED_MODEL_CONFIG'):
            text = settings.ORDERED_MODEL_CONFIG.get('up_html', 'up')
        return '<a href="%s">%s</a>' % (link, text)
    admin_up_link.allow_tags = True

    def admin_down_link(self):
        after = self.ordered_filter()
        after = after.filter(order__gt=self.order)
        if len(after) == 0:
            return ''

        content_type = ContentType.objects.get_for_model(self)
        link = reverse('ordered_model.views.ordered_item_down',
            args=(content_type.id, self.id))
        text = 'down'
        if hasattr(settings, 'ORDERED_MODEL_CONFIG'):
            text = settings.ORDERED_MODEL_CONFIG.get('down_html', 'down')
        return '<a href="%s">%s</a>' % (link, text)
    admin_down_link.allow_tags = True


@receiver(pre_save)
def ordered_model_pre_save_handler(sender, **kwargs):
    # This method ensures the integrity of the order field
    #
    # IMPORTANT: 
    #
    #   As the integrity is managed in a signal, any changes to other objects
    #   in this signal CANNOT invoke the save() method.  Django does not
    #   invoke signals on update() so that MUST be used
    obj = kwargs['instance']
    if not isinstance(obj, OrderedModel):
        # have registered against everyone because django doesn't handle
        # inheritence in signals, if not an OM, do nothing
        return

    if kwargs.get('raw', False):
        # fixtures use "raw", assume they set the order correctly
        return

    if not obj.id:
        # newly created object, make sure to set the order appropriately
        order = getattr(obj, 'order', None)
        items = obj.ordered_filter().order_by('order').select_for_update()
        count = items.count()
        if count == 0:
            # no items, insert at top regardless of what was asked for
            obj.order = 1
        elif order == None or order > count + 1:
            # no order specified, or too large, insert at the end
            obj.order = count + 1
        else:
            with transaction.atomic():
                # if you get here a specific order was requested, need to
                # re-order everything after it in the list
                changes = items[order - 1:]
                changes = changes.values('pk')
                obj.__class__.objects.filter(pk__in=changes).update(
                    order=models.F('order') + 1)

        # in case this object gets called saved again, update last known
        obj._last_known_order = obj.order
        return

    # obj exists already, check if we're attempting to change the order
    if obj.order != obj._last_known_order:
        if obj.order < 1:
            obj.order = 1

        with transaction.atomic():
            items = obj.ordered_filter().order_by('order').select_for_update()
            count = items.count()
            if obj.order > count:
                obj.order = count
                # need to recheck in case the corrected value isn't really
                # changed anymore
                if obj.order != obj._last_known_order:
                    return

            if obj.order < obj._last_known_order:
                changes = items[obj.order - 1:obj._last_known_order -1]
                delta = 1
            else:
                changes = items[obj._last_known_order:obj.order]
                delta = -1

            if len(changes):
                # django doesn't allow you to update a slice, so reform the
                # query based on the slice and update that
                changes = changes.values('pk')
                obj.__class__.objects.filter(pk__in=changes).update(
                    order=models.F('order') + delta)

            # correct last known in case same object is called again
            for item in items:
                item._last_known_order = item.order
