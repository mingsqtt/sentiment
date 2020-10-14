
from response_generator import *

class DialogContext:
    def __init__(self, client_id, channel, latest_doc):
        self.client_id = client_id
        self.channel = channel
        self.latest_doc = latest_doc
        self.data = {"vessel": None, "voyage": None, "eta_date": None, "eta_time": None, "in_date": None, "in_time": None, "out_date": None,
                     "out_time": None, "qty": None, "foot_size": None, "cntr_type": None, "addr": [], "comp": None, "cntr_nums": [],
                     "job_codes": []}
        self.temp_data = None
        self.confirm_what = ""
        self.confirm_content = ""

_ctx = None


def get_context(client_id, channel, current_doc):
    global _ctx
    if _ctx is None:
        _ctx = DialogContext(client_id, channel, current_doc)
        return _ctx, True
    else:
        _ctx.latest_doc = current_doc
        return _ctx, False


def clear_context(ctx):
    global _ctx
    _ctx = None


def update_context(ctx):
    pass


def exec_hand_over(ctx, gen_response=True):
    if gen_response:
        return inform_hand_over(ctx)
    else:
        return None


def process_book_intent(ctx):
    return ""


def process_input_intent(ctx):
    return ""


def process_update_intent(ctx):
    return ""


def process_update_later_intent(ctx):
    return ""


def process_confirm_intent(ctx):
    return "", True


def process_decline_intent(ctx):
    return "", True


def process_weak_intent(ctx, weak_intent):
    ctx.confirm_what = "intent"
    ctx.confirm_content = weak_intent
    return ask_to_confirm_intent(ctx, weak_intent)


def process_other_intent(ctx, gen_response=True):
    response = exec_hand_over(ctx, gen_response)
    clear_context(ctx)
    return response