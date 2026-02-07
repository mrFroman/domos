from .advert_menu import advert_menu
from .contract_menu import (
    create_contract_menu,
    confirm_contract,
    start_passport_flow,
    upload_passport_page,
    upload_passport_photo,
    upload_registration_photo,
    check_processing_status,
)
from .events_menu import events_menu, event_detail
from .main_menu import main_menu
from .meeting_menu import meeting_booking
from .helpful_menu import helpful_menu, download_files
from .invite_menu import invite_menu
from .rules_menu import rules_menu
from .payment_menu import download_offer, payment_menu, payment_sub_check
from .lawyer_menu import lawyer_menu, upload_lawyer_file
from .irbis import irbis_menu, irbis_payment_check
from .telegram_auth import login, telegram_auth_callback, check_telegram_token
from .phone_auth import phone_login, phone_enter_telegram_id, phone_verify_code, resend_code
from .admin_dashboard import (
    admin_add_contact,
    admin_add_realtor,
    admin_advert_management,
    admin_advert_queries,
    admin_advert_requests,
    admin_analytics,
    admin_broadcast,
    admin_feedback_table,
    admin_find_user,
    admin_legal_requests,
    admin_paid,
    admin_unpaid,
)
from .new_sections import (
    assistant_view,
    assistant_chat_api,
    services_view,
    subscriptions_view,
    my_requests_view,
    admin_dashboard_view,
)
