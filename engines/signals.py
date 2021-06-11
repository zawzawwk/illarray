from uuid import UUID
import time
from django.db import transaction
from django.db.models import Value as V
from django.db.models.functions import Concat
from django.db.models import Max
from django.utils.timezone import now
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, pre_delete
from clouds.signals import materialized, executed, monitored, destroyed, selected
from clouds.signals import tidy_operation, select_operation
from clouds import utils
from .import models
from clouds.models import Instance, INSTANCE_STATUS, InstanceOperation, INSTANCE_OPERATION, OPERATION_STATUS, Mount, Group, GroupOperation

from django.dispatch import Signal
scaled_out = Signal(providing_args=["instance","name"])

@receiver(scaled_out)
def log(sender,instance,name,**kwargs):
    print('SIGNAL INFO:', sender._meta.app_label, sender._meta.verbose_name, instance, name)

@receiver(materialized, sender=Group)
@receiver(post_save, sender=models.Cluster)
def scale_out(sender,instance,**kwargs):
    if sender==models.Cluster:
        if not kwargs['created'] or instance.deleting: return
        instance.scale_one_step()
        return    
    for cluster in instance.cluster_set.select_for_update():
        cluster.built_time=now()
        cluster.save()
        old_steps=cluster.get_ready_steps().exclude(pk=instance.pk)
        old_hosts='\n'.join([step.hosts for ins in old_steps])
        for step in old_steps:
            step.update_remedy_script(
                utils.remedy_script_hosts_add(instance.hosts)
            )
        instance.update_remedy_script(
            utils.remedy_script_hosts_add(old_hosts)
        )
        if cluster.scale.remedy_script:
            instance.update_remedy_script(
                cluster.scale.remedy_script
            )
        GroupOperation(
            operation=INSTANCE_OPERATION.start.value,
            target=instance,
            status=OPERATION_STATUS.running.value,
        ).save()
        scaled_out.send(sender=models.Cluster, instance=cluster, name='scaled_out')

# @receiver(post_save, sender=models.Step)
# def step_out(sender,instance,**kwargs):
#     if sender==models.Step:
#         if not kwargs['created'] or instance.deleting: return
#         instance.built_time = now()
#         instance.save()

# @receiver(post_save, sender=models.Cluster)
# @receiver(post_save, sender=Instance)
# def scale_cluster(sender,instance,**kwargs):
#     if sender==Instance and instance.cluster_set.filter().exists():
#         pass#TODO
#     instance.built_time=None
#     instance.status=INSTANCE_STATUS.building.value
#     instance.save()

# @receiver(pre_delete, sender=Instance)
# def scale_in_cluster(sender,instance,**kwargs):
#     if not instance.ready: return
#     for cluster in instance.cluster_set.all():
#         for ins in cluster.instances.all():
#             ins.update_remedy_script(
#                 utils.remedy_script_hosts_remove(instance.hosts_record)
#             )

@receiver(destroyed, sender=Group)
@transaction.atomic
def destroy_cluster(sender,instance,**kwargs):
    for cluster in models.Cluster.objects.select_for_update().filter(
        deleting=True,
    ):
        if not cluster.steps.all().exists():
            cluster.delete()
            destroyed.send(sender=models.Cluster, instance=cluster, name='destroyed')

@receiver(monitored, sender=Group)
@receiver(post_save, sender=models.ClusterOperation)
@receiver(executed, sender=models.ClusterOperation)
def monitor_status(sender, instance, **kwargs):
    if sender==Group:
        if instance.deleting: return
        for cluster in instance.cluster_set.all():
            status=cluster.steps.all().aggregate(Max('status'))['status__max']
            models.Cluster.objects.filter(pk=cluster.pk).update(status=status)
            cluster.refresh_from_db()
            monitored.send(sender=models.Cluster, instance=cluster, name='monitored')
    else:
        if 'created' in kwargs:
            if kwargs['created'] and instance.status==OPERATION_STATUS.running.value and not instance.serial:
                instance.target.monitor()
        else:
            instance.target.monitor()

pre_save.connect(tidy_operation,sender=models.ClusterOperation)
monitored.connect(select_operation,sender=models.Cluster)
@receiver(selected, sender=models.ClusterOperation)
def execute_operation(sender,instance,**kwargs):
    instance.execute()

#TODO use threading join to reduce last singal check
@receiver(executed, sender=GroupOperation)
@transaction.atomic
def close_cluster_operation(sender, instance, **kwargs):
    for running_op in models.ClusterOperation.objects.select_for_update().filter(
        batch_uuid=instance.batch_uuid,
        started_time__isnull=False,
        completed_time__isnull=True
    ):
        if not running_op.get_remain_oprations().exists():
            running_op.completed_time=now()
            running_op.status=running_op.get_status()
            running_op.save()
            executed.send(sender=models.ClusterOperation, instance=running_op, name='executed')

        # elif instance.operation==models.COMPONENT_OPERATION.stop.value:
        #     print(instance.target.stop())
        # elif instance.operation==models.COMPONENT_OPERATION.restart.value:
        #     raise Exception('not implemented yet')
        # else:
        #     raise Exception('illegal operation')
        # instance.completed_time=now()

# @receiver(post_save, sender=models.EngineOperation)
# def operate_engine(sender,instance,created,**kwargs):
#     if created:
#         if not instance.engine.enabled:
#             raise Exception('cannot operate disabled engine')
#         if instance.operation==models.COMPONENT_OPERATION.start.value:
#             instance.engine.start(instance.pilot)
#         elif instance.operation==models.COMPONENT_OPERATION.stop.value:
#             instance.engine.stop(instance.pilot)
#         instance.completed_time=now()
#         instance.save()