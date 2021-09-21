import time
from uuid import uuid4
from enum import Enum
from threading import Thread
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from clouds.models import StaticModel, Image, Instance, Mount, INSTANCE_STATUS, INSTANCE_OPERATION, OPERATION_STATUS, InstanceBlueprint, InstanceOperation, OperatableMixin, OperationModel, Group, GroupOperation
from django.utils.functional import cached_property
from django.db import transaction
from clouds.base.models import M2MOperatableMixin, M2MOperationModel

import importlib
class Stack(StaticModel):
    _driver=models.CharField(max_length=50)
    host=models.ForeignKey(Instance,on_delete=models.PROTECT)
    @cached_property
    def driver(self):
        return importlib.import_module(self._driver)
    def import_engine(self):
        es=self.driver.list_engines(self.host.ipv4)
        for e in es:
            name=e['name']
            if Engine.objects.filter(name=name,stack=self).exists(): continue
            eg=Engine(
                name=name,
                stack=self,
                owner=self.owner,
                description=e['description'],
                remark='auto imported'
            )
            eg.save()
            cpns=self.driver.list_components(self.host.ipv4,name)
            for c in cpns:
                name=c['name']
                if Component.objects.filter(name=name,stack=self).exists(): continue
                cpn=Component(
                    name=name,
                    stack=self,
                    type=c['type'],
                    owner=self.owner,
                    remark='auto imported'
                )
                [{'href': 'http://10.0.88.64:8080/api/v1/stacks/HDP/versions/2.5/services/HBASE/components/HBASE_CLIENT', 'StackServiceComponents':{'advertise_version': True, 'bulk_commands_display_name': '', 'bulk_commands_master_component_name': '', 'cardinality': '1+', 'component_category': 'CLIENT', 'component_name': 'HBASE_CLIENT', 'custom_commands': [], 'decommission_allowed': False, 'display_name': 'HBase Client', 'has_bulk_commands_definition': False, 'is_client':True, 'is_master': False, 'reassign_allowed': False, 'recovery_enabled': False, 'rolling_restart_supported': False, 'service_name':'HBASE', 'stack_name': 'HDP', 'stack_version': '2.5'}, 'dependencies': []}, {'href': 'http://10.0.88.64:8080/api/v1/stacks/HDP/versions/2.5/services/HBASE/components/HBASE_MASTER', 'StackServiceComponents': {'advertise_version': True, 'bulk_commands_display_name': '', 'bulk_commands_master_component_name': '', 'cardinality': '1+', 'component_category': 'MASTER', 'component_name': 'HBASE_MASTER', 'custom_commands': ['DECOMMISSION'], 'decommission_allowed': False, 'display_name': 'HBase Master', 'has_bulk_commands_definition': False, 'is_client': False, 'is_master': True, 'reassign_allowed': False, 'recovery_enabled': False, 'rolling_restart_supported':False, 'service_name': 'HBASE', 'stack_name': 'HDP', 'stack_version': '2.5'}, 'dependencies': [{'href': 'http://10.0.88.64:8080/api/v1/stacks/HDP/versions/2.5/services/HBASE/components/HBASE_MASTER/dependencies/HDFS_CLIENT', 'Dependencies': {'component_name': 'HDFS_CLIENT', 'dependent_component_name': 'HBASE_MASTER', 'dependent_service_name': 'HBASE', 'stack_name': 'HDP', 'stack_version': '2.5'}}, {'href': 'http://10.0.88.64:8080/api/v1/stacks/HDP/versions/2.5/services/HBASE/components/HBASE_MASTER/dependencies/ZOOKEEPER_SERVER', 'Dependencies': {'component_name': 'ZOOKEEPER_SERVER', 'dependent_component_name': 'HBASE_MASTER', 'dependent_service_name': 'HBASE', 'stack_name': 'HDP', 'stack_version': '2.5'}}]}, {'href': 'http://10.0.88.64:8080/api/v1/stacks/HDP/versions/2.5/services/HBASE/components/HBASE_REGIONSERVER', 'StackServiceComponents': {'advertise_version': True, 'bulk_commands_display_name': 'RegionServers', 'bulk_commands_master_component_name': 'HBASE_MASTER', 'cardinality': '1+', 'component_category': 'SLAVE', 'component_name':'HBASE_REGIONSERVER', 'custom_commands': [], 'decommission_allowed': True, 'display_name': 'RegionServer', 'has_bulk_commands_definition': True, 'is_client': False, 'is_master': False, 'reassign_allowed': False, 'recovery_enabled': False, 'rolling_restart_supported': False, 'service_name': 'HBASE', 'stack_name': 'HDP', 'stack_version': '2.5'}, 'dependencies': []}, {'href': 'http://10.0.88.64:8080/api/v1/stacks/HDP/versions/2.5/services/HBASE/components/PHOENIX_QUERY_SERVER', 'StackServiceComponents': {'advertise_version':True, 'bulk_commands_display_name': '', 'bulk_commands_master_component_name': '', 'cardinality': '0+', 'component_category': 'SLAVE', 'component_name': 'PHOENIX_QUERY_SERVER', 'custom_commands': [], 'decommission_allowed': False, 'display_name': 'Phoenix Query Server', 'has_bulk_commands_definition': False, 'is_client': False,'is_master': False, 'reassign_allowed': False, 'recovery_enabled': False, 'rolling_restart_supported': False, 'service_name': 'HBASE', 'stack_name': 'HDP', 'stack_version': '2.5'}, 'dependencies': []}]
                cpn.save()
                eg.components.add(cpn)


class COMPONENT_STATUS(Enum):
    null=0 #unknown
    active=1
    block=2
    suspend=3
    stop=4
    breakdown=5
    pause=6
    instance_lost=7

class COMPONENT_TYPE(Enum):
    master="master"
    slave="slave"
    client="client"

class COMPONENT_OPERATION(Enum):
    start="start"
    stop="stop"
    # restart="restart"

class Component(StaticModel):
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    images=models.ManyToManyField(Image)# every image is required for a single component to run.
    type=models.CharField(max_length=50,choices=[(type.value,type.name) for type in COMPONENT_TYPE])
    stack=models.ForeignKey(Stack,on_delete=models.PROTECT)
    endpoint=models.CharField(max_length=200,default='',blank=True)

class Engine(StaticModel):#TODO make Engine customizable in the ui
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    stack=models.ForeignKey(Stack,on_delete=models.PROTECT)
    components=models.ManyToManyField(Component)# every component is required for a single engine to run.
    description=models.TextField(max_length=5120,blank=True,default='')
    def start(self, pilot):
        print(utils.ambari_service_start('admin','admin',pilot.portal,self.name.upper()))
    def stop(self, pilot):
        print(utils.ambari_service_stop('admin','admin',pilot.portal,self.name.upper()))
    def status(self, pilot):
        state=utils.ambari_service_status('admin','admin',pilot.portal,self.name.upper())['ServiceInfo']['state']
        if state=='INSTALLED':
            return COMPONENT_STATUS.stop.value
        elif state=='STARTED':
            return COMPONENT_STATUS.running.value
        else:
            return COMPONENT_STATUS.null.value

class Scale(StaticModel):
    init_blueprints=models.ManyToManyField(InstanceBlueprint,related_name="initialized_scales",verbose_name='initial blueprints')
    step_blueprints=models.ManyToManyField(InstanceBlueprint,related_name="stepped_scales",blank=True,verbose_name='scale-out blueprints')
    _remedy_script=models.TextField(max_length=5120,default="",blank=True,verbose_name='initial remedy script')
    _remedy_script_scale_out=models.TextField(max_length=5120,default="",blank=True,verbose_name='scale-out remedy script')
    _remedy_script_scale_in=models.TextField(max_length=5120,default="",blank=True,verbose_name='scale-in remedy script')
    auto=models.BooleanField(default=False)
    def __str__(self):
        return "{}/{}".format(
            self.name,
            'auto' if self.auto else 'manual',
        )
    @cached_property
    def remedy_script_scale_out(self):
        return "###scale-out remedy {}: {}###\n{}\n".format(
            self._meta.verbose_name,
            self.name,
            self._remedy_script_scale_out
        ) if self._remedy_script_scale_out else ""
    @cached_property
    def remedy_script_scale_in(self):
        return "###scale-in remedy {}: {}###\n{}\n".format(
            self._meta.verbose_name,
            self.name,
            self._remedy_script_scale_in
        ) if self._remedy_script_scale_in else ""
    @cached_property
    def init_size(self):
        q=0
        for ib in self.init_blueprints.all():
            q+=ib.quantity
        return q
    @cached_property
    def step_size(self):
        q=0
        for ib in self.step_blueprints.all():
            q+=ib.quantity
        return q
    @cached_property
    def available_engines(self):
        hosted_imgs=Image.objects.filter(
            instance_blueprints__in=self.init_blueprints.all()
        ).distinct()
        hosted_components=Component.objects.exclude(
            images__in=Image.objects.exclude(pk__in=hosted_imgs)
        )
        return Engine.objects.exclude(
            components__in=Component.objects.exclude(pk__in=hosted_components)
        ).order_by('id').distinct()
    def scale(self, owner, current_step=0, remark=None):
        step=Group(owner=owner)
        step.save()
        if not current_step:#init
            if not remark: remark='initialized from scale: {}'.format(self.name)
            step.remark=remark
            for ib in self.init_blueprints.all():
                inss=ib.launch(owner=owner, remark=remark)
                step.instances.add(*inss)
        else:
            if not remark: remark='scaled from scale: {}'.format(self.name)
            step.remark=remark
            for ib in self.step_blueprints.all():
                next_number=ib.quantity*(current_step-1)+1
                if self.init_blueprints.filter(pk=ib.pk).exists():
                    next_number+=ib.quantity
                inss=ib.launch(owner=owner, next_number=next_number, remark=remark)
                step.instances.add(*inss)
        step.remark=remark
        step.save()
        return step

def scales_of_user(self):
    excluded_blueprints=InstanceBlueprint.objects.exclude(pk__in=self.blueprints())
    return Scale.objects.exclude(
        Q(init_blueprints__in=excluded_blueprints) | Q(step_blueprints__in=excluded_blueprints)
    ).filter(enabled=True).filter(Q(public=True) | Q(owner=self)).distinct()
User.scales=scales_of_user

class Cluster(models.Model,M2MOperatableMixin):
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    name=models.CharField(max_length=50)
    scale=models.ForeignKey(Scale,on_delete=models.PROTECT)
    engines=models.ManyToManyField(Engine,blank=True)
    steps=models.ManyToManyField(Group,blank=True,editable=False)
    remedy_script_todo=models.TextField(max_length=51200,default="",blank=True)
    remark = models.CharField(blank=True,null=True,max_length=100)
    public=models.BooleanField(default=False)
    owner=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    created_time=models.DateTimeField(auto_now_add=True)
    built_time=models.DateTimeField(blank=True, null=True, editable=False)
    status= models.PositiveIntegerField(choices=[(status.value,status.name) for status in INSTANCE_STATUS],default=INSTANCE_STATUS.building.value,editable=False)
    deleting = models.BooleanField(default=False,editable=False)
    class Meta:
        unique_together = ('name', 'owner')
    def __str__(self):
        return "{}".format(self.name)
    @staticmethod
    def get_operation_model():
        return ClusterOperation
    @property
    def operatables(self):
        return self.steps.all()
    @property
    def ready(self):
        return self.built_time
    @property
    def building(self):
        return self.built_time and not self.ready
    def get_ready_steps(self):
        return self.steps.filter(built_time__isnull=False)
    def get_instances(self):
        return Instance.objects.filter(group__in=self.steps.filter()).distinct()
    def get_ready_instances(self):
        return Instance.objects.filter(group__in=self.get_ready_steps()).distinct()
    @cached_property
    def portal(self):#TODO formalize, opt perf.
        if not self.ready: raise Exception('cluster not ready')
        mi=self.get_ready_instances().filter(image__name__contains='master1')
        if mi.exists(): return "http://"+str(mi[0].ipv4)+':8080'
        return None
    @cached_property
    def engines_unselected(self):
        return Engine.objects.all().difference(self.engines.all())
    @transaction.atomic
    def scale_one_step(self):# the only way to scale cluster
        cluster=self.__class__.objects.select_for_update().get(pk=self.pk)
        step=cluster.scale.scale(
            owner=cluster.owner,
            current_step=cluster.steps.count(),
            remark='cluster: '+cluster.name
        )
        cluster.steps.add(step)
    def delete(self, *args, **kwargs):
        if not self.ready:
            print('WARNNING: delete {} under building'.format(self._meta.verbose_name))
        operatables=self.operatables
        if operatables.exists():
            self.deleting=True
            self.save()
            for operatable in operatables:
                operatable.destroy_script_todo=self.scale.remedy_script_scale_in
                operatable.save()
                operatable.delete()
        else:
            super().delete(*args, **kwargs)
    # def start(self):
    #     return utils.ambari_service_start_all('admin','admin',self.portal)#TODO use credential args
    # def stop(self):
    #     return utils.ambari_service_stop_all('admin','admin',self.portal)
    # def add_selected_engines(self):
    #     for e in self.engines.all():
    #         #set maintaince mode instead of removing
    #         utils.ambari_service_maintenance_off('admin','admin',self.portal,e.name.upper())
    # def remove_unselected_engines(self):
    #     for e in self.engines_unselected:
    #         #set maintaince mode instead of removing
    #         utils.ambari_service_maintenance_on('admin','admin',self.portal,e.name.upper())
    # @cached_property
    # def init_size(self):
    #     size=0
    #     for ib in self.blueprint.instance_blueprints.all():
    #         size+=ib.quantity
    #     return size
    def find_instance(self,hostname):
        matched_ins=self.instances.filter(hostname=hostname)
        return matched_ins[0] if matched_ins.exists() else None

def clusters_of_user(self):
    return Cluster.objects.filter(Q(public=True) | Q(owner=self))
User.clusters=clusters_of_user

def steps_of_user(self):
    return Group.objects.filter(cluster__in=self.clusters()).distinct()
User.steps=steps_of_user

class ClusterOperation(M2MOperationModel):
    target=models.ForeignKey(Cluster,on_delete=models.CASCADE)
    class Meta:
        verbose_name='cluster operation'
    @staticmethod
    def get_sub_operation_model():
        return GroupOperation

class StepOperation(GroupOperation):
    class Meta(GroupOperation.Meta):
        proxy = True
        verbose_name = 'operation'
    def __str__(self):
        return "Cluster {}/Step {}/{}/{}".format(self.cluster,self.number,self.operation,self.status)
    @cached_property
    def cluster(self):
        return self.target.cluster_set.first()
    @cached_property
    def number(self):
        steps=self.cluster.steps.all()
        l=steps.count()
        target_pk=self.target.pk
        for i in range(l):
            if steps[i].pk==target_pk:
                return i+1