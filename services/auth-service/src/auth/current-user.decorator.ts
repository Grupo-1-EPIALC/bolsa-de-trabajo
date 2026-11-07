import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { UserRole } from '../users/user-role';

export interface AuthenticatedUser {
  sub: string;
  role: UserRole;
  /** token_version de la cuenta al emitir el token (ausente en tokens anteriores = 0). */
  tv?: number;
}

export const CurrentUser = createParamDecorator(
  (_data: unknown, context: ExecutionContext): AuthenticatedUser =>
    context.switchToHttp().getRequest<{ user: AuthenticatedUser }>().user,
);
