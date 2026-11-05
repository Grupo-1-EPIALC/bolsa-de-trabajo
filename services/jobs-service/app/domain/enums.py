"""Enumeraciones del contrato común de perfil/oferta/match."""

from enum import StrEnum


class JobStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class JobStatusFilter(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    ALL = "all"


class RequirementKind(StrEnum):
    REQUIRED = "required"
    DESIRED = "desired"
    EXCLUDING = "excluding"


class Seniority(StrEnum):
    NO_EXPERIENCE = "no_experience"
    TRAINEE = "trainee"
    JUNIOR = "junior"
    SEMI_SENIOR = "semi_senior"
    SENIOR = "senior"


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


class SalaryAdjustment(StrEnum):
    NONE = "none"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    BY_AGREEMENT = "by_agreement"


class PaymentMode(StrEnum):
    LOCAL = "local"
    USD = "usd"
    USD_PAID_IN_LOCAL = "usd_paid_in_local"


class VariableCompensationType(StrEnum):
    BONUS = "bonus"
    COMMISSION = "commission"
    PROFIT_SHARING = "profit_sharing"


class TravelAvailability(StrEnum):
    NONE = "none"
    OCCASIONAL = "occasional"
    FREQUENT = "frequent"


class InvoicingStatus(StrEnum):
    MONOTRIBUTO = "monotributo"
    RESPONSABLE_INSCRIPTO = "responsable_inscripto"
    NONE = "none"
    TO_REGISTER = "to_register"
