import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { UserRole } from '../users/user-role';

export interface AuthenticatedUser {
  sub: string;
  role: UserRole;
}

export const CurrentUser = createParamDecorator(
  (_data: unknown, context: ExecutionContext): AuthenticatedUser =>
    context.switchToHttp().getRequest<{ user: AuthenticatedUser }>().user,
);
