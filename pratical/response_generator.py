import numpy as np


def format_msg_template(templates, *args):
    template = np.random.choice(templates, 1, p=[1/len(templates)]*len(templates))[0]
    if (args is not None) and (len(args) > 0):
        return template.format(*args)
    else:
        return template


hand_over_templates_email = [
    "Dear Sir/Mdm,\n\nI will forward your request to my colleague to help you further.\n\nBest Regards",
    "Dear Sir/Mdm,\n\nPerhaps, my colleague will be able to assist you better.\n\nBest Regards",
    "Dear Sir/Mdm,\n\nLet me hand over this case to my colleague to help you further.\n\nBest Regards"
]
hand_over_templates_chat = [
    "Give me a second, I will let my colleague to further help you.",
    "Hold on, let me transfer to my colleague. He would assist you better."
    "Wait a moment, my colleague would like to help you on this case."
]


def inform_hand_over(ctx):
    if ctx.channel == "email":
        response = format_msg_template(hand_over_templates_email)
    else:
        response = format_msg_template(hand_over_templates_chat)
    return response


booking_completed_templates_email = [
    "Dear Sir/Mdm,\n\nYour booking of container has been made successfully. XXX-XXX-XXX is the job code created for your reference.\n\nThank you!\n\nBest Regards"
]

booking_completed_templates_chat = [
    "It's all set. Your booking has been made successfully. XXX-XXX-XXX is the job code created for your reference. Thank you!",
    "Alright. We have successfully created a booking for your with job code XXX-XXX-XXX. Thank you!"
]


def inform_booking_completed(ctx):
    if ctx.channel == "email":
        response = format_msg_template(booking_completed_templates_email)
    else:
        response = format_msg_template(booking_completed_templates_chat)
    return response


data_updated_templates_email = [
    "Dear Sir/Mdm,\n\nThe job details have been updated successfully for XXX-XXX-XXX.\n\nBest Regards"
]

data_updated_templates_chat = [
    "OK. Job details has been updated successfully for {}.",
    "No problem. Job details has been updated for {}!"
]


def inform_data_updated(ctx):
    if ctx.channel == "email":
        response = format_msg_template(data_updated_templates_email, ctx.data["job_code"])
    else:
        response = format_msg_template(data_updated_templates_chat, ctx.data["job_code"])
    return response


confirm_intent_templates_email = {
    "book": [
        "Would you like to make a booking of container trucking?\n\nBest Regards"
    ],
    "update": [
        "Would you like to change the trucking details?\n\nBest Regards"
    ]
}

confirm_intent_templates_chat = {
    "book": [
        "Would you like to make a booking of container trucking?",
        "Did you mean you would like to make a booking of container trucking?"
    ],
    "update": [
        "Would you like to make changes to a booking?",
        "Did you mean you would like to change the trucking job details?"
    ]
}


def ask_to_confirm_intent(ctx, intent):
    if ctx.channel == "email":
        response = format_msg_template(confirm_intent_templates_email[intent])
    else:
        response = format_msg_template(confirm_intent_templates_chat[intent])
    return response


confirm_replace_booking_templates_email = [
    "Dear Sir/Mdm,\n\nIt appears you might want to make another new booking.\n\nDo you want to abandon the previously specified job details and start over again? If yes, we will start over again, otherwise, we will continue the current booking.\n\nPlease kindly clarify.\n\nBest Regards"
]

confirm_replace_booking_templates_chat = [
    "Did you mean you want to make another new booking? If yes, we will start over again, otherwise, we will continue the current booking."
]


def ask_to_confirm_replace_booking(ctx):
    if ctx.channel == "email":
        response = format_msg_template(confirm_replace_booking_templates_email)
    else:
        response = format_msg_template(confirm_replace_booking_templates_chat)
    return response


confirm_booking_details_templates_email = [
    "Dear Sir/Mdm,\n\nPlease confirm if the following booking details is correct:\n\n{}\n\nBest Regards"
]

confirm_booking_details_templates_chat = [
    "We are almost there. Does the following booking details look alright for you?\n\n{}",
    "One last step, is the following booking details alright for you?\n\n{}"
]


def ask_to_confirm_booking(ctx):
    details = ""
    if ctx.data["foot_size"] is not None:
        details += "Container Specification: {} {}\n".format(ctx.data["foot_size"], ctx.data["cntr_type"] if ctx.data["cntr_type"] is not None else "")
    if ctx.data["qty"] is not None:
        details += "Quantity: {}\n".format(ctx.data["qty"])
    if len(ctx.data["cntr_nums"]) > 0:
        details += "Container No.: {}\n".format(ctx.data["cntr_nums"][0])
    if ctx.data["in_date"] is not None:
        details += "Truck-In: {} {}\n".format(ctx.data["in_date"], ctx.data["in_time"] if ctx.data["in_time"] is not None else "")
    if ctx.data["out_date"] is not None:
        details += "Truck-Out: {} {}\n".format(ctx.data["out_date"], ctx.data["out_time"] if ctx.data["out_time"] is not None else "")
    if ctx.data["eta_date"] is not None:
        details += "ETA: {} {}\n".format(ctx.data["eta_date"], ctx.data["eta_time"] if ctx.data["eta_time"] is not None else "")
    if ctx.data["vessel"] is not None:
        details += "Vessel: {}\n".format(ctx.data["vessel"])
    if ctx.data["voyage"] is not None:
        details += "Voyage: {}\n".format(ctx.data["voyage"])
    if len(ctx.data["addr"]) > 0:
        details += "Location: {}\n".format(ctx.data["addr"][0].replace("\n", ", "))
    if ctx.data["comp"] is not None:
        details += "End Customer: {}\n".format(ctx.data["comp"])

    if ctx.channel == "email":
        response = format_msg_template(confirm_booking_details_templates_email, details)
    else:
        response = format_msg_template(confirm_booking_details_templates_chat, details)
    return response


confirm_update_details_templates_email = [
    "Dear Sir/Mdm,\n\nPlease confirm if the following changes are correct:\n\n{}\n\nBest Regards"
]

confirm_update_details_templates_chat = [
    "Does the following changes look correct?\n\n{}"
]


def ask_to_confirm_update(ctx):
    details = ""
    if len(ctx.data["job_codes"]) > 0:
        details += "Job Code: {}\n".format(ctx.data["job_codes"][0])
    if ctx.data["foot_size"] is not None:
        details += "Container Specification: {} {}\n".format(ctx.data["foot_size"],
                                                             ctx.data["cntr_type"] if ctx.data["cntr_type"] is not None else "")
    if ctx.data["qty"] is not None:
        details += "Quantity: {}\n".format(ctx.data["qty"])
    if len(ctx.data["cntr_nums"]) > 0:
        details += "Container No.: {}\n".format(ctx.data["cntr_nums"][0])
    if ctx.data["in_date"] is not None:
        details += "Truck-In: {} {}\n".format(ctx.data["in_date"], ctx.data["in_time"] if ctx.data["in_time"] is not None else "")
    if ctx.data["out_date"] is not None:
        details += "Truck-Out: {} {}\n".format(ctx.data["out_date"], ctx.data["out_time"] if ctx.data["out_time"] is not None else "")
    if ctx.data["eta_date"] is not None:
        details += "ETA: {} {}\n".format(ctx.data["eta_date"], ctx.data["eta_time"] if ctx.data["eta_time"] is not None else "")
    if ctx.data["vessel"] is not None:
        details += "Vessel: {}\n".format(ctx.data["vessel"])
    if ctx.data["voyage"] is not None:
        details += "Voyage: {}\n".format(ctx.data["voyage"])
    if len(ctx.data["addr"]) > 0:
        details += "Location: {}\n".format(ctx.data["addr"][0].replace("\n", ", "))
    if ctx.data["comp"] is not None:
        details += "End Customer: {}\n".format(ctx.data["comp"])

    if ctx.channel == "email":
        response = format_msg_template(confirm_update_details_templates_email, details)
    else:
        response = format_msg_template(confirm_update_details_templates_chat, details)
    return response


ask_for_missing_templates_email = [
    "Dear Sir/Mdm,\n\nWe would need you to provide the following details to complete the booking:\n\n{}\n\nBest Regards"
]

ask_for_missing_templates_chat = {
    "vessel": [
        "What is the vessel name?",
    ],
    "voyage": [
        "What is the voyage number?",
    ],
    "vessel_voyage": [
        "Can I know the vessel name and voyage number?",
    ],
    "eta_date": [
        "When is the vessel estimated time of arrival?"
    ],
    "in_date": [
        "When is the truck-in date and time?"
    ],
    "qty_spe": [
        "What type of container is required, and the quantity?"
    ],
    "qty": [
        "How many containers do you need?"
    ],
    "foot_size": [
        "What's the foot size of the container required?"
    ],
    "ctnr_type": [
        "What type of container is required?"
    ],
    "addr": [
        "Where is the delivery location?"
    ]
}


def ask_for_missing_slots(ctx, missing_slots):
    if ctx.channel == "email":
        label_mapping = {
            "vessel": "Vessel Name",
            "voyage": "Voyage Number",
            "vessel_voyage": "Vessel/Voyage",
            "eta_date": "Vessel ETA",
            "in_date": "Truck-In Date/Time",
            "qty_spe": "Container Type & Quantity",
            "qty": "Container Quantity",
            "foot_size": "Container Foot Size",
            "ctnr_type": "Container Type",
            "addr": "Location"
        }

        labels = ""
        for slot in missing_slots:
            labels += " - {}\n".format(label_mapping[slot])

        response = format_msg_template(ask_for_missing_templates_email, labels)
    else:
        response = format_msg_template(ask_for_missing_templates_chat[missing_slots[0]])
    return response


ask_for_job_code_templates_email = [
    "Dear Sir/Mdm,\n\nPlease let us know the job code that you want to change for.\n\nBest Regards"
]

ask_for_job_code_templates_chat = [
    "Which job code are you referring to?"
]


def ask_for_which_job(ctx):
    if ctx.channel == "email":
        response = format_msg_template(ask_for_job_code_templates_email)
    else:
        response = format_msg_template(ask_for_job_code_templates_chat)
    return response


def ask_for_slot_data_and_job_code_for_update(ctx):
    response = "Please let us know what change you want to make, for which job code."
    return response


def say_greeting(ctx):
    response = "How can I help you?"
    return response
