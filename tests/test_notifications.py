from fieldservice_notifications import WorkOrderNotification


def test_channel_is_bound_to_technician():
    item = WorkOrderNotification("WO-7", "tech-3", "en_route", "arrival-photo", "Call customer")
    assert item.channel == "technician-tech-3"
    assert item.dispatch_status == "en_route"
