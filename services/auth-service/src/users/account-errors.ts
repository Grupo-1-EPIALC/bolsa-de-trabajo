import { ForbiddenException } from '@nestjs/common';

/**
 * 403 con `error.code = "ACCOUNT_SUSPENDED"` (el filtro global arma el código desde `error`).
 * Se usa sólo después de validar las credenciales, para no revelar el estado de cuentas ajenas.
 */
export function accountSuspendedError(): ForbiddenException {
  return new ForbiddenException({
    statusCode: 403,
    message: 'Tu cuenta está suspendida. Contactá a la administración.',
    error: 'Account Suspended',
  });
}
