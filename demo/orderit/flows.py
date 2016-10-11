from viewflow import flow
from viewflow.base import this, Flow
from viewflow.flow.views import UpdateProcessView
from viewflow.lock import select_for_update_lock, CacheLock

from .models import OrderItCompleteProjectProcess, BangusTask
from . import views


class OrderItCompleteProjectFlow(Flow):
    process_class = OrderItCompleteProjectProcess
    task_class = BangusTask
    lock_impl = CacheLock()

    summary_template = """foo--bar---"""

    start = (
        flow.Start(views.start_view)
            .Permission('orderit.can_start_order')
        .Next(this.split_review_and_amend)
    )

    split_review_and_amend = (
        flow.Split()
        .Next(this.user_amend_order)
        .Next(this.admin_review_order)
    )

    user_amend_order = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_amended']
        ).Assign(lambda act: act.process.created_by)
        .Next(this.join_review_and_amend)
    )

    admin_review_order = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_verified']
        ).Permission('orderit.can_verify_order').Next(
            this.manager_confirm_order
        )
    )

    manager_confirm_order = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_confirmed']
        ).Permission('orderit.can_confirm_order').Next(
            this.join_review_and_amend
        )
    )

    join_review_and_amend = (
        flow.Join()
        .Next(this.deploy_virtual_machines)
    )

    deploy_virtual_machines = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_deployed']
        ).Permission('orderit.can_deploy_virtual_machines').Next(
            this.install_vm_software
        )
    )

    install_vm_software = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['vms_software_installed']
        ).Assign(lambda act: act.process.created_by).Next(
            this.fix_vm_security
        )
    )

    fix_vm_security = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['security_fixed']
        ).Assign(lambda act: act.process.created_by).Next(
            this.confirm_vm_security
        )
    )

    confirm_vm_security = (
        # TODO: flip the security_fixed flag if the confirmation fails.
        flow.View(
            views.OrderCompleteProjectView,
            fields=['security_confirmed']
        ).Permission('orderit.can_confirm_security_status').Next(
            this.check_security
        )
    )

    check_security = (
        flow.If(cond=lambda act: act.process.is_security_clear())
        .Then(this.alloc_external_ip)
        .Else(this.fix_vm_security)
    )

    alloc_external_ip = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['external_ip']
        ).Assign(lambda act: act.process.created_by).Next(
            this.confirm_external_ip
        )
    )

    confirm_external_ip = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['external_ip_confirmed']
        ).Permission('orderit.can_confirm_external_ip').Next(
            this.check_external_ip
        )
    )

    check_external_ip = (
        flow.If(cond=lambda act: act.process.is_external_ip_confirmed())
        .Then(this.deploy_external_ip)
        .Else(this.alloc_external_ip)
    )

    deploy_external_ip = (
        flow.View(
            views.OrderCompleteProjectView,
            fields=['external_ip_deployed']
        ).Permission('orderit.can_deploy_external_ip').Next(
            this.end
        )
    )

    end = flow.End()
