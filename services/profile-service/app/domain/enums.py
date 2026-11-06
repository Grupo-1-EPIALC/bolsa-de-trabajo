"""Enumeraciones del contrato común perfil ↔ oferta ↔ match (§3 de la estructura común)."""

from enum import StrEnum


class ProfileStatus(StrEnum):
    DRAFT = "draft"  # faltan datos obligatorios
    COMPLETE = "complete"  # listo para matching y para generar el CV


class WorkSchedule(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    HOURLY = "hourly"
    FLEXIBLE = "flexible"


class WorkModality(StrEnum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"


class EmploymentType(StrEnum):
    EMPLOYEE = "employee"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    TRAINEE = "trainee"


class ContractDuration(StrEnum):
    PERMANENT = "permanent"
    FIXED_TERM = "fixed_term"
    PROJECT = "project"
    SEASONAL = "seasonal"


class AvailabilityStart(StrEnum):
    IMMEDIATE = "immediate"
    WITHIN_15_DAYS = "within_15_days"
    WITHIN_30_DAYS = "within_30_days"
    TO_AGREE = "to_agree"


class Shift(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    WEEKEND = "weekend"
    ROTATING = "rotating"


class Seniority(StrEnum):
    NO_EXPERIENCE = "no_experience"
    TRAINEE = "trainee"
    JUNIOR = "junior"
    SEMI_SENIOR = "semi_senior"
    SENIOR = "senior"


class SkillCategory(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    TOOL = "tool"
    METHODOLOGY = "methodology"


class LanguageLevel(StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"
    NATIVE = "native"


class EducationLevel(StrEnum):
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    UNIVERSITY = "university"
    POSTGRADUATE = "postgraduate"
    COURSE = "course"


class EducationStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"


class Currency(StrEnum):
    ARS = "ARS"
    USD = "USD"


class SalaryPeriod(StrEnum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    PROJECT = "project"


class SalaryVisibility(StrEnum):
    PUBLIC = "public"
    ON_MATCH = "on_match"
    HIDDEN = "hidden"


class PaymentMode(StrEnum):
    LOCAL = "local"
    USD = "usd"
    USD_PAID_IN_LOCAL = "usd_paid_in_local"


class TravelAvailability(StrEnum):
    NONE = "none"
    OCCASIONAL = "occasional"
    FREQUENT = "frequent"


class InvoicingStatus(StrEnum):
    MONOTRIBUTO = "monotributo"
    RESPONSABLE_INSCRIPTO = "responsable_inscripto"
    NONE = "none"
    TO_REGISTER = "to_register"


class ProfileVisibility(StrEnum):
    PUBLIC_TO_COMPANIES = "public_to_companies"
    ONLY_APPLIED = "only_applied"
    HIDDEN = "hidden"


class JobSearchStatus(StrEnum):
    ACTIVE = "active"
    OPEN_TO_OFFERS = "open_to_offers"
    NOT_LOOKING = "not_looking"


class LinkType(StrEnum):
    LINKEDIN = "linkedin"
    GITHUB = "github"
    PORTFOLIO = "portfolio"
    OTHER = "other"


class DataSource(StrEnum):
    CV_AI = "cv_ai"  # sugerido por la IA a partir del CV y aceptado por el usuario
    MANUAL = "manual"  # cargado a mano
