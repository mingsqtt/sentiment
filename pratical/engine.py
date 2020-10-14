import numpy as np
import pandas as pd
from datetime import datetime
import re

from text_processor import *
from response_generator import *


class DialogContext:
    def __init__(self, client_id, channel, current_doc):
        self.client_id = client_id
        self.channel = channel
        self.current_doc = current_doc
        self.data = {"vessel": None, "voyage": None, "eta_date": None, "eta_time": None, "in_date": None, "in_time": None, "out_date": None,
                     "out_time": None, "qty": None, "foot_size": None, "cntr_type": None, "addr": [], "comp": None, "cntr_nums": [],
                     "job_codes": []}
        self.temp_data = None
        self.confirm_what = ""
        self.confirm_content = ""
        self.slot_mention_history = []
        self.slot_filling_history = []
        self.expecting_slots = []

    def to_string(self):
        string = "Newly Extracted Data:\n"
        for key in self.current_doc.data:
            val = self.current_doc.data[key]
            if (val is not None) and (val != "") and ((type(val) != list) or (len(val) > 0)):
                string += "{}: {}\n".format(key, val)

        string += "\nContext Data:\n"
        for key in self.data:
            val = self.data[key]
            if (val is not None) and (val != "") and ((type(val) != list) or (len(val) > 0)):
                string += "{}: {}\n".format(key, val)

        if len(self.slot_filling_history) > 0:
            string += "\nLast 4 Filled Slots: {}\n".format(self.slot_filling_history[-4:])

        if self.confirm_what != "":
            string += "Confirm What: " + self.confirm_what + "\n"
            if type(self.confirm_content) == dict:
                string += "Confirm Content:\n"
                val = self.confirm_content[key]
                if (val is not None) and (val != "") and ((type(val) != list) or (len(val) > 0)):
                    string += "{}: {}\n".format(key, val)
            else:
                string += "Confirm Content: " + self.confirm_content + "\n"

        if self.temp_data is not None:
            string += "Temp Data:\n{}".format(self.temp_data)

        return string


def any_slot_filled(slots_data):
    return (slots_data["vessel"] is not None) or (slots_data["voyage"] is not None) or (slots_data["eta_date"] is not None) or (
            slots_data["eta_time"] is not None) or (slots_data["in_date"] is not None) or (
                   slots_data["in_time"] is not None) or (slots_data["out_date"] is not None) or (slots_data["out_time"] is not None) or (
                   slots_data["qty"] is not None) or (
                   slots_data["foot_size"] is not None) or (
                   slots_data["cntr_type"] is not None) or (len(slots_data["addr"]) > 0) or (slots_data["comp"] is not None) or (
                   len(slots_data["cntr_nums"]) > 0) or (len(slots_data["job_codes"]) > 0)


_ctx = None


def get_context(client_id, channel, current_doc):
    global _ctx
    if _ctx is None:
        _ctx = DialogContext(client_id, channel, current_doc)
        return _ctx, True
    else:
        _ctx.current_doc = current_doc
        return _ctx, False


def clear_context(ctx):
    global _ctx
    _ctx = None


def save_context(ctx):
    global _ctx
    _ctx = ctx


def do_hand_over(ctx, gen_response=True):
    if gen_response:
        return inform_hand_over(ctx)
    else:
        return None


def do_create_booking(ctx):
    return inform_booking_completed(ctx)


def do_update_booking(ctx):
    return inform_data_updated(ctx)


def merge_data(merge_from, merge_to, slot_fill_history):
    for key in merge_from:
        val = merge_from[key]
        if type(val) == list:
            if len(val) > 0:
                merge_to[key] = val
                slot_fill_history.append(key)
        elif (val is not None) and (val != ""):
            merge_to[key] = val
            slot_fill_history.append(key)
    return merge_to


def validate_data(ctx, merge_with_data=None):
    if merge_with_data is not None:
        ctx.data = merge_data(merge_with_data, ctx.data, ctx.slot_filling_history)
    invalid_slots = list()
    response = ""
    return invalid_slots, response


def check_missing_slots(ctx):
    missing_slots = list()

    for compulsory_slot in [("qty_spe", ["foot_size", "cntr_type", "qty"]), "in_date", "addr", ("vessel_voyage", ["vessel", "voyage"]), "eta_date"]:
        if type(compulsory_slot) == tuple:
            missing_sub_slots = list()
            for slot in compulsory_slot[1]:
                if (ctx.data[slot] is None) or (ctx.data[slot] == ""):
                    missing_sub_slots.append(slot)
            if len(missing_sub_slots) == len(compulsory_slot[1]):
                missing_slots.append(compulsory_slot[0])
            elif len(missing_sub_slots) > 0:
                missing_slots.extend(missing_sub_slots)
        elif (ctx.data[compulsory_slot] is None) or (ctx.data[compulsory_slot] == "") or ((type(ctx.data[compulsory_slot]) == list) and (len(ctx.data[compulsory_slot]) == 0)):
            missing_slots.append(compulsory_slot)

    if len(missing_slots) == 0:
        response = ask_to_confirm_booking(ctx)
    elif ctx.channel == "chat":
        missing_slots = [missing_slots[0]]
        ctx.expecting_slots = missing_slots
        response = ask_for_missing_slots(ctx, missing_slots)
    elif ctx.channel == "email":
        ctx.expecting_slots = missing_slots
        response = ask_for_missing_slots(ctx, missing_slots)
    return missing_slots, response


def merge_validate_and_confirm_booking(ctx, merge_with_data):
    invalid_slots, response = validate_data(ctx, merge_with_data)
    if len(invalid_slots) == 0:
        missing_slots, response = check_missing_slots(ctx)
        if len(missing_slots) == 0:
            ctx.confirm_what = "booking_data"
            ctx.confirm_content = ctx.data
        else:
            ctx.expecting_slots = missing_slots
            ctx.slot_mention_history.extend(missing_slots)
            ctx.confirm_what = ""
    else:
        ctx.expecting_slots = invalid_slots
        ctx.slot_mention_history.extend(invalid_slots)
        ctx.confirm_what = ""
    return response


def process_book_intent(ctx):
    if any_slot_filled(ctx.data):
        response = ask_to_confirm_replace_booking(ctx)
        ctx.confirm_what = "new_booking"
        ctx.confirm_content = ctx.current_doc.data
        ctx.temp_data = ctx.current_doc.data
    elif any_slot_filled(ctx.current_doc.data):
        response = merge_validate_and_confirm_booking(ctx, ctx.current_doc.data)
    else:
        missing_slots, response = check_missing_slots(ctx)
        ctx.expecting_slots = missing_slots
        ctx.slot_mention_history.extend(missing_slots)
        ctx.confirm_what = ""
    return response


def process_input_intent(ctx):
    if any_slot_filled(ctx.data):
        if len(ctx.data["job_codes"]) == 0:
            response = merge_validate_and_confirm_booking(ctx, ctx.current_doc.data)
        else:
            invalid_slots, response = validate_data(ctx, ctx.current_doc.data)
            if len(invalid_slots) == 0:
                ctx.confirm_what = "update_data"
                ctx.confirm_content = ctx.data
                response = ask_to_confirm_update(ctx)
            else:
                ctx.confirm_what = ""
    else:
        response = ask_for_which_job(ctx)
        ctx.temp_data = ctx.current_doc.data
        ctx.expecting_slots = ["job_code"]
        ctx.slot_mention_history.extend(ctx.expecting_slots)
        ctx.confirm_what = ""
    return response


def process_update_intent(ctx):
    if any_slot_filled(ctx.current_doc.data):
        if any_slot_filled(ctx.data):
            if len(ctx.data["job_codes"]) == 0:
                response = merge_validate_and_confirm_booking(ctx, ctx.current_doc.data)
            else:
                invalid_slots, response = validate_data(ctx, ctx.current_doc.data)
                if len(invalid_slots) == 0:
                    ctx.confirm_what = "update_data"
                    ctx.confirm_content = ctx.data
                    response = ask_to_confirm_update(ctx)
                else:
                    ctx.confirm_what = ""
        elif len(ctx.current_doc.data["job_codes"]) == 1:
            if ctx.temp_data is not None:
                ctx.data = merge_data(merge_data(ctx.current_doc.data, ctx.temp_data, []), ctx.data, ctx.slot_filling_history)
            else:
                ctx.data = merge_data(ctx.current_doc.data, ctx.data, ctx.slot_filling_history)
            invalid_slots, response = validate_data(ctx, None)
            if len(invalid_slots) == 0:
                ctx.confirm_what = "update_data"
                ctx.confirm_content = ctx.data
                response = ask_to_confirm_update(ctx)
            else:
                ctx.confirm_what = ""
        else:
            response = ask_for_which_job(ctx)
            ctx.temp_data = ctx.current_doc.data
            ctx.expecting_slots = ["job_code"]
            ctx.slot_mention_history.extend(ctx.expecting_slots)
            ctx.confirm_what = ""
    else:
        response = ask_for_slot_data_and_job_code_for_update(ctx)
        ctx.expecting_slots = ["job_code"]
        ctx.slot_mention_history.extend(ctx.expecting_slots)
        ctx.confirm_what = ""
    return response


def process_confirm_intent(ctx):
    if ctx.confirm_what == "intent":
        ctx.confirm_what = ""
        if ctx.confirm_content == "book":
            if type(ctx.temp_data) == dict:
                ctx.data = merge_data(merge_data(ctx.current_doc.data, ctx.temp_data, []), ctx.data, ctx.slot_filling_history)
                ctx.temp_data = None
            return process_book_intent(ctx), False
        elif ctx.confirm_content == "update":
            if type(ctx.temp_data) == dict:
                ctx.data = merge_data(merge_data(ctx.current_doc.data, ctx.temp_data, []), ctx.data, ctx.slot_filling_history)
            return process_update_intent(ctx), False
    elif ctx.confirm_what == "booking_data":
        ctx.confirm_what = ""
        ctx.data = merge_data(merge_data(ctx.current_doc.data, ctx.confirm_content, []), ctx.data, ctx.slot_filling_history)
        return do_create_booking(ctx), True
    elif ctx.confirm_what == "update_data":
        ctx.confirm_what = ""
        ctx.data = merge_data(merge_data(ctx.current_doc.data, ctx.confirm_content, []), ctx.data, ctx.slot_filling_history)
        return do_update_booking(ctx), True
    elif ctx.confirm_what == "new_booking":
        ctx.confirm_what = ""
        if type(ctx.confirm_content) is dict:
            return merge_validate_and_confirm_booking(ctx, ctx.confirm_content), False
        else:
            return merge_validate_and_confirm_booking(ctx, None), False
    else:
        ctx.confirm_what = ""
        return None, True


def process_decline_intent(ctx):
    if ctx.confirm_what == "intent":
        ctx.confirm_what = ""
        return do_hand_over(ctx, True), True
    elif ctx.confirm_what == "booking_data":
        ctx.confirm_what = ""
        if any_slot_filled(ctx.current_doc.data):
            return merge_validate_and_confirm_booking(ctx, ctx.current_doc.data), False
        else:
            return do_hand_over(ctx, True), True
    elif ctx.confirm_what == "update_data":
        ctx.confirm_what = ""
        if any_slot_filled(ctx.current_doc.data):
            return process_update_intent(ctx), False
        else:
            return do_hand_over(ctx, True), True
    elif ctx.confirm_what == "new_booking":
        ctx.confirm_what = ""
        if len(ctx.data["job_codes"]) == 0:
            if (type(ctx.confirm_content) is dict) and any_slot_filled(ctx.confirm_content):
                return merge_validate_and_confirm_booking(ctx, ctx.confirm_content), False
            else:
                return merge_validate_and_confirm_booking(ctx, ctx.current_doc.data), False
        else:
            if (type(ctx.confirm_content) is dict) and any_slot_filled(ctx.confirm_content):
                invalid_slots, response = validate_data(ctx, ctx.confirm_content)
            else:
                invalid_slots, response = validate_data(ctx, ctx.current_doc.data)

            if len(invalid_slots) == 0:
                ctx.confirm_what = "update_data"
                ctx.confirm_content = ctx.data
                response = ask_to_confirm_update(ctx)
            else:
                ctx.confirm_what = ""
            return response, False
    elif any_slot_filled(ctx.current_doc.data):
        ctx.confirm_what = ""
        return process_update_intent(ctx), False
    else:
        ctx.confirm_what = ""
        return None, True


def process_weak_intent(ctx, weak_intent):
    ctx.confirm_what = "intent"
    ctx.confirm_content = weak_intent
    ctx.temp_data = ctx.current_doc.data
    return ask_to_confirm_intent(ctx, weak_intent)


def process_other_intent(ctx, gen_response=True):
    response = do_hand_over(ctx, gen_response)
    clear_context(ctx)
    return response


def process_incoming_text(text, client_id="", channel="email"):
    if channel == "email":
        doc = EmailMessage(text, client_id).latest_doc
    else:
        doc = Document(text, client_id=client_id)

    ctx, is_new_ctx = get_context(client_id, channel, doc)
    has_info_extracted, has_update_later_intent = extract_info(doc, ctx.expecting_slots)
    intent_probs = np.array(
        [detect_simple_input_intent(doc, has_info_extracted), predict_book_intent(doc), predict_update_intent(doc),
         detect_confirm_intent(doc, ctx),
         detect_decline_intent(doc)])
    if channel == "chat":
        intent_probs = np.append(intent_probs, detect_greeting_intent(doc))
        max_ind = np.argmax(intent_probs)
        intent = ["input", "book", "update", "confirm", "decline", "greet"][max_ind]
    else:
        max_ind = np.argmax(intent_probs)
        intent = ["input", "book", "update", "confirm", "decline"][max_ind]
    intent_prob = intent_probs[max_ind]

    ctx.current_doc = doc
    if is_new_ctx:
        print("======== new context ===========")
    print(ctx.to_string())

    if (intent != "input") and (len(ctx.expecting_slots) > 0):
        if ctx.expecting_slots.__contains__("vessel_voyage") and ((doc.data["vessel"] is not None) or (doc.data["voyage"] is not None)):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("vessel") and (doc.data["vessel"] is not None):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("voyage") and (doc.data["voyage"] is not None):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("qty_spe") and ((doc.data["qty"] is not None) or (doc.data["foot_size"] is not None) or (doc.data["cntr_type"] is not None)):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("qty") and (doc.data["qty"] is not None):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("foot_size") and (doc.data["foot_size"] is not None):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("cntr_type") and (doc.data["cntr_type"] is not None):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("in_date") and (doc.data["in_date"] is not None):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("eta_date") and (doc.data["eta_date"] is not None):
            intent = "input"
            intent_prob = 3
        elif ctx.expecting_slots.__contains__("addr") and (len(doc.data["addr"]) > 0):
            intent = "input"
            intent_prob = 3

    if intent != "update":
        if ctx.expecting_slots.__contains__("job_code") and (len(doc.data["job_codes"]) > 0):
            intent = "update"
            intent_prob = 3
        elif (intent == "book") and (len(ctx.data["job_codes"]) > 0):
            intent = "update"
            intent_prob = 3

    if has_update_later_intent:
        intent = "input"
        intent_prob = 3

    ctx.expecting_slots = []

    if (intent_prob > 0) and (intent_prob < 0.5):
        print("Detected Weak !! Intent: " + intent)
        response = process_weak_intent(ctx, intent)
        print("Response:", response, "\n")
        save_context(ctx)
        return response
    elif intent_prob >= 0.5:
        print("Detected Intent: " + intent)
        if intent == "book":
            response = process_book_intent(ctx)
            save_context(ctx)
        elif intent == "input":
            response = process_input_intent(ctx)
            save_context(ctx)
        elif intent == "update":
            response = process_update_intent(ctx)
            save_context(ctx)
        elif intent == "confirm":
            response, end_of_dialog = process_confirm_intent(ctx)
            if end_of_dialog:
                clear_context(ctx)
            else:
                save_context(ctx)
        elif intent == "decline":
            response, end_of_dialog = process_decline_intent(ctx)
            if end_of_dialog:
                clear_context(ctx)
            else:
                save_context(ctx)
        elif intent == "greet":
            response = say_greeting(ctx)
            save_context(ctx)
        else:
            raise Exception("Unknown intent {}".format(intent))
        print("Response:", response, "\n")
        return response
    else:
        print("Detected Intent: Unknown")
        response = process_other_intent(ctx, True)
        print("Response:", response, "\n")
        return response


clear_context(_ctx)
for msg in [
    "can i book a 20'GP container for wed?",
    "please deliver it to 12 Science Park Drive",
    "the vessel is Titanic, and the voyage number is S233",
    "24/2/2020 6pm please",
    "sorry, the eta isn't 24/2/2020 any more, change it to 25/2/2020 instead",
    "yes, change it",
    "looks alright, go a head please"
]:
    print(msg)
    process_incoming_text(msg)
    print("-----------\n")


clear_context(_ctx)
for msg in [
    "can i book a container for my customer's?",
    "just 1 20 foot container",
    "20 foot GP container",
    "23/02/2323",
    "eta is 23/Jan/2020, please truck in on the next day. address: 10 Buroh Street, Singapore 627564. vessel Titanic voy.S3423",
    "yes, thank you"
]:
    print(msg)
    process_incoming_text(msg)
    print("-----------\n")



clear_context(_ctx)
for msg in [
    "i need a container on monday, can help me arrange for it?",
    "just 1 20 foot container",
    "20 foot GP container",
    "eta is 23/Jan/2020, please truck in on the next day. address: 10 Buroh Street, Singapore 627564. vessel Titanic voy.S3423",
    "Sorry, the eta should be 25/12/2020 instead of 23th"
]:
    print(msg)
    process_incoming_text(msg)
    print("-----------\n")



clear_context(_ctx)
for msg in [
    "i want a container",
    "just 1 20 foot container",
    "20 foot GP container",
    "eta is 23/Jan/2020, please truck in on the next day. address: 10 Buroh Street, Singapore 627564. vessel Titanic voy.S3423",
    "Sorry, the eta should be 25/12/2020 instead of 23th",
    "the container size is to be changed to 40 foot please",
    "the voyage number is also wrong. it is actually S0009",
    "ok"
]:
    print(msg)
    process_incoming_text(msg)
    print("-----------\n")



clear_context(_ctx)
for msg in [
    "i want a 20 foot GP container",
    "please truck in on the next day. address: 10 Buroh Street, Singapore 627564. vessel Titanic, the eta is to be confirmed",
    "will let you know the it at later stage",
    "yes"
]:
    print(msg)
    process_incoming_text(msg)
    print("-----------\n")




clear_context(_ctx)
for msg in [
    "the vessel Titanic is delayed to 26 Dec 2020, please reschedule the truck in date",
    "IM-234-2343 please",
    "also the truck in date shall be delayed to 27 Dec accordingly",
    "yes, thank you"
]:
    print(msg)
    process_incoming_text(msg)
    print("-----------\n")



clear_context(_ctx)
for msg in [
    "for IM-234-2343, the vessel Titanic is delayed to 26 Dec 2020, please reschedule the truck in date",
    "also the truck in date shall be delayed to 27 Dec accordingly",
    "no, the eta is 26 Dec 2020",
    "yes, thank you"
]:
    print(msg)
    process_incoming_text(msg)
    print("-----------\n")




clear_context(_ctx)
for msg in [
    "hi there",
    "can we reschedule the truck in date for IM-234-2343?",
    "yes",
    "please reschedule it to tomorrow",
    "no, i want to reschedule the truck in date to tomorrow",
    "yes"
]:
    print(msg)
    process_incoming_text(msg, channel="chat")
    print("-----------\n")



clear_context(_ctx)
for msg in [
    "Hi Hui Min Sek,\nPls ref to attached cartage advice and booking confirmation\nREQUIRE CLEAN & DRY WITH GOOD CONDITION CONTAINER\n1X40GP\nTruck in :  22 JUL (WED)\nTruck out: 23 JUL (THURS)\nPls park @\nAdvanced Regional Centre\nTampines LogisPark\n1 Greenwich Drive\nARC Warehouse Block 1, Level 2\nBay 1 to 9.\nBest Regards,\nRegina Jebulan\nExport Transactional Ops\nDHL Global Forwarding (S) Pte Ltd\n1 Changi South Street 2 Level 4\nDHL Distribution Centre\nSingapore 486760"
]:
    print(msg)
    process_incoming_text(msg, channel="email")
    print("-----------\n")


clear_context(_ctx)
for msg in [
    "Please refer on the revised BC, please proceed collection of empty tomorrow morning.\nPlease truck out on 29-Oct."
]:
    print(msg)
    process_incoming_text(msg, channel="email")
    print("-----------\n")



clear_context(_ctx)
for msg in [
    "I’m checking with he carrier to update on 24th Oct.\nWill keep you posted."
]:
    print(msg)
    process_incoming_text(msg, channel="email")
    print("-----------\n")


clear_context(_ctx)
for msg in [
    "Please note that 28/10 is PH in-lieu.\nKindly advise if trucking out on 29/10 is possible.",
    "EX-234-2343",
    "yes"
]:
    print(msg)
    process_incoming_text(msg, channel="email")
    print("-----------\n")




clear_context(_ctx)
for msg in [
    "Dear Jennifer,\nPlease stand by empty trucking 100x40’RH on 31-Dec on ward.\nShall send trucking order once finalized\nTrucking from: Pacific Trans depot 15A Tuas South Ave 12 Singapore 637133\nDeliver location: PSA terminal.\nLoading vessel details as below:-\nVSL: VICTOR V.S0FR1N\nETA SIN: 02.01.2020 @ 1700HRS\nPOD: PHDCT"
]:
    print(msg)
    process_incoming_text(msg, channel="email")
    print("-----------\n")



clear_context(_ctx)
for msg in [
    "Dear All,\nPlease arrange to truck out the empty container accordingly as below without further delay. \nFrom TLH\n1.)  NYKU3452868\nAddress:\n60 Tuas Bay Drive, Singapore 637568\n***pls truck out empty containers  within 24 hrs from the time notifide***\nBest Regards,"
]:
    print(msg)
    process_incoming_text(msg, channel="email")
    print("-----------\n")


clear_context(_ctx)
for msg in [
    "Dear Jason,\nAs spoken, we confirmed the below.\nTrucking and truck out – must use side loader and container need to be grounded.\nTruck in – 24 July 2020\nTruck out loaded  - 28 July 2020 for TT",
    "As spoken, I will arrange the delivery to your customer’s site during office hours (Preferably before 12) on Friday (24th Jul)."
]:
    print(msg)
    process_incoming_text(msg, channel="email")
    print("-----------\n")



clear_context(_ctx)
for msg in [
    "Dear Averyl,  \nHP: 8288 0798\nPlease find the attached docs for 1x40’ container trucking to below premises ASAP.\nHock Cheong Forwarding @ 1765 Geylang Bahru #01-02 Kallang Distripack.\nContainer number: TCKU9352718  / 40’HC   \nWe had transfer the payment to shipping line.\nPlease check port-net status accordingly and arrange container delivery to us ASAP. Thanks.Thanks & regards,",
    "40'GP",
    "asap",
    "no"
]:
    print(msg)
    process_incoming_text(msg, channel="email")
    print("-----------\n")

