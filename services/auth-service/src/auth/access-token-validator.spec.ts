import { UnauthorizedException } from '@nestjs/common';
import { UserRole } from '../users/user-role';
import { AccessTokenValidator, TokenVersionReader } from './access-token-validator';

const ADMIN_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';

function validatorWith(current: { role: UserRole; tokenVersion: number } | null) {
  const versions: TokenVersionReader = { current: jest.fn().mockResolvedValue(current) };
  return { validator: new AccessTokenValidator(versions), versions };
}

describe('AccessTokenValidator (revocación de access tokens)', () => {
  it('UT-AUTH-10 acepta un token con la token_version vigente', async () => {
    const { validator, versions } = validatorWith({ role: UserRole.ADMIN, tokenVersion: 2 });
    await expect(
      validator.validate({ sub: ADMIN_ID, role: UserRole.ADMIN, tv: 2 }),
    ).resolves.toEqual({ sub: ADMIN_ID, role: UserRole.ADMIN, tv: 2 });
    expect(versions.current).toHaveBeenCalledWith(ADMIN_ID);
  });

  it('UT-AUTH-11 un token de admin emitido antes del reset deja de valer al instante', async () => {
    // El reset (o el cambio de clave) subió token_version de 2 a 3.
    const { validator } = validatorWith({ role: UserRole.ADMIN, tokenVersion: 3 });
    await expect(
      validator.validate({ sub: ADMIN_ID, role: UserRole.ADMIN, tv: 2 }),
    ).rejects.toMatchObject({
      status: 401,
      response: expect.objectContaining({ error: 'TOKEN_REVOKED' }),
    });
  });

  it('UT-AUTH-12 el token de una cuenta borrada (o inexistente) da 401', async () => {
    const { validator } = validatorWith(null);
    await expect(
      validator.validate({ sub: ADMIN_ID, role: UserRole.ADMIN, tv: 0 }),
    ).rejects.toBeInstanceOf(UnauthorizedException);
  });

  it('rechaza un token cuyo rol ya no coincide con el de la cuenta', async () => {
    const { validator } = validatorWith({ role: UserRole.STUDENT, tokenVersion: 0 });
    await expect(
      validator.validate({ sub: ADMIN_ID, role: UserRole.ADMIN, tv: 0 }),
    ).rejects.toMatchObject({ status: 401 });
  });

  it('los tokens anteriores al cambio (sin tv) valen como versión 0', async () => {
    const { validator } = validatorWith({ role: UserRole.STUDENT, tokenVersion: 0 });
    await expect(validator.validate({ sub: ADMIN_ID, role: UserRole.STUDENT })).resolves.toEqual({
      sub: ADMIN_ID,
      role: UserRole.STUDENT,
      tv: 0,
    });
    const bumped = validatorWith({ role: UserRole.STUDENT, tokenVersion: 1 });
    await expect(
      bumped.validator.validate({ sub: ADMIN_ID, role: UserRole.STUDENT }),
    ).rejects.toMatchObject({ status: 401 });
  });

  it('rechaza payloads inválidos sin consultar la base', async () => {
    const { validator, versions } = validatorWith({ role: UserRole.ADMIN, tokenVersion: 0 });
    await expect(
      validator.validate({ sub: '', role: UserRole.ADMIN, tv: 0 }),
    ).rejects.toBeInstanceOf(UnauthorizedException);
    await expect(
      validator.validate({ sub: ADMIN_ID, role: 'root' as UserRole, tv: 0 }),
    ).rejects.toBeInstanceOf(UnauthorizedException);
    await expect(
      validator.validate({ sub: ADMIN_ID, role: UserRole.ADMIN, tv: 1.5 }),
    ).rejects.toBeInstanceOf(UnauthorizedException);
    expect(versions.current).not.toHaveBeenCalled();
  });
});
