import logging
import contextvars

request_id_var = contextvars.ContextVar("request_id", default="-")
user_id_var = contextvars.ContextVar("user_id", default="-")
company_id_var = contextvars.ContextVar("company_id", default="-")
route_var = contextvars.ContextVar("route", default="-")
method_var = contextvars.ContextVar("method", default="-")

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.company_id = company_id_var.get()
        record.route = route_var.get()
        record.method = method_var.get()
        return True
