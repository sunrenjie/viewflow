from django.utils.translation import ugettext_lazy as _

from viewflow import flow
from viewflow.base import this, Flow
from viewflow.flow.views import UpdateProcessView
from viewflow.lock import select_for_update_lock, CacheLock

from .models import OrderItCompleteProjectProcess, BangusTask
from . import views


class OrderItCompleteProjectFlowStart(flow.Start):
    # subclassing for the sole purpose of customization of the task title
    task_title = _("Start an OrderIt complete project process")


class OrderItCompleteProjectFlow(Flow):
    process_class = OrderItCompleteProjectProcess
    task_class = BangusTask
    lock_impl = CacheLock()

    summary_template = """foo--bar---"""

    start = (
        OrderItCompleteProjectFlowStart(views.start_view)
            .Permission('orderit.can_start_order')
        .Next(this.user_amend_order)
    )

    user_amend_order = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_amended', 'vms_request_for_review']
        ).Assign(lambda act: act.process.created_by)
        .Next(this.check_vms_request_for_review)
    )

    check_vms_request_for_review = (
        flow.If(cond=lambda act: act.process.order.vms_request_for_review)
        .Then(this.admin_review_order)
        .Else(this.user_amend_order)
    )

    admin_review_order = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_verified']
        ).Permission('orderit.can_verify_order').Next(
            this.check_vms_verification)
    )

    check_vms_verification = (
        flow.If(cond=lambda act: act.process.order.vms_verified)
        .Then(this.manager_confirm_order)
        .Else(this.user_amend_order)
    )

    manager_confirm_order = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_confirmed']
        ).Permission('orderit.can_confirm_order').Next(
            this.check_vms_confirmation
        )
    )

    check_vms_confirmation = (
        flow.If(cond=lambda act: act.process.order.vms_confirmed)
        .Then(this.deploy_virtual_machines)
        .Else(this.user_amend_order)
    )

    deploy_virtual_machines = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_deployed']
        ).Permission('orderit.can_deploy_virtual_machines').Next(
            this.install_vm_software)
    )

    install_vm_software = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_software_installed']
        ).Assign(lambda act: act.process.created_by).Next(
            this.fix_vm_security)
    )

    fix_vm_security = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['security_fixed']
        ).Assign(lambda act: act.process.created_by).Next(
            this.confirm_vm_security)
    )

    confirm_vm_security = (
        # TODO: flip the security_fixed flag if the confirmation fails.
        flow.View(
            views.OrderCompleteProjectView,
            fields=['security_confirmed']
        ).Permission('orderit.can_confirm_security_status').Next(
            this.check_security_confirmation)
    )

    check_security_confirmation = (
        flow.If(cond=lambda act: act.process.is_security_clear())
        .Then(this.request_external_ip)
        .Else(this.fix_vm_security)
    )

    request_external_ip = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['external_ip']
        ).Assign(lambda act: act.process.created_by).Next(
            this.confirm_external_ip)
    )

    confirm_external_ip = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['external_ip_confirmed']
        ).Permission('orderit.can_confirm_external_ip').Next(
            this.check_external_ip)
    )

    check_external_ip = (
        flow.If(cond=lambda act: act.process.is_external_ip_confirmed())
        .Then(this.deploy_external_ip)
        .Else(this.request_external_ip)
    )

    deploy_external_ip = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['external_ip_deployed']
        ).Permission('orderit.can_deploy_external_ip').Next(
            this.end)
    )

    end = flow.End()
