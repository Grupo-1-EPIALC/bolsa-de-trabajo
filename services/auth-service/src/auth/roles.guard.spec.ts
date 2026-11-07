import { ExecutionContext, ForbiddenException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { UserRole } from '../users/user-role';
import { RolesGuard } from './roles.guard';

function context(role?: UserRole): ExecutionContext {
  return {
    getHandler: () => undefined,
    getClass: () => undefined,
    switchToHttp: () => ({ getRequest: () => ({ user: role ? { sub: 'u1', role } : undefined }) }),
  } as unknown as ExecutionContext;
}

describe('RolesGuard', () => {
  const reflector = { getAllAndOverride: jest.fn() } as unknown as Reflector & {
    getAllAndOverride: jest.Mock;
  };
  const guard = new RolesGuard(reflector);

  it('deja pasar al rol pedido', () => {
    reflector.getAllAndOverride.mockReturnValue([UserRole.ADMIN]);
    expect(guard.canActivate(context(UserRole.ADMIN))).toBe(true);
  });

  it('rechaza con 403 a otro rol', () => {
    reflector.getAllAndOverride.mockReturnValue([UserRole.ADMIN]);
    expect(() => guard.canActivate(context(UserRole.STUDENT))).toThrow(ForbiddenException);
  });

  it('sin @Roles no restringe', () => {
    reflector.getAllAndOverride.mockReturnValue(undefined);
    expect(guard.canActivate(context(UserRole.COMPANY))).toBe(true);
  });
});
