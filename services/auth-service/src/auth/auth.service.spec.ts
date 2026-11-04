import { Repository, EntityManager, DataSource } from 'typeorm';
import * as argon2 from 'argon2';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { generateKeyPairSync } from 'node:crypto';
import { JwtService } from '@nestjs/jwt';
import { Company } from '../users/company.entity';
import { User } from '../users/user.entity';
import { UserRole } from '../users/user-role';
import { ActionToken, ActionTokenPurpose } from './action-token.entity';
import { AuthService } from './auth.service';
import { RefreshSession } from './refresh-session.entity';

function createService() {
  const queryBuilder = {
    addSelect: jest.fn().mockReturnThis(),
    leftJoinAndSelect: jest.fn().mockReturnThis(),
    where: jest.fn().mockReturnThis(),
    orWhere: jest.fn().mockReturnThis(),
    getOne: jest.fn(),
    update: jest.fn().mockReturnThis(),
    set: jest.fn().mockReturnThis(),
    execute: jest.fn().mockResolvedValue({ affected: 1 }),
  };
  const manager = {
    save: jest.fn(async (_entity: unknown, entity: unknown) => entity),
    create: jest.fn((_entity: unknown, value: unknown) => value),
    findOne: jest.fn(),
    update: jest.fn().mockResolvedValue({ affected: 1 }),
    createQueryBuilder: jest.fn(() => queryBuilder),
  };
  const dataSource = {
    transaction: jest.fn(async (callback: (entityManager: EntityManager) => Promise<unknown>) =>
      callback(manager as unknown as EntityManager),
    ),
  };
  const users = {
    create: jest.fn((value: Partial<User>) => Object.assign(new User(), value, { id: 'user-1' })),
    save: jest.fn(async (value: User) => value),
    findOne: jest.fn(),
    createQueryBuilder: jest.fn(() => queryBuilder),
  };
  const companies = {
    exists: jest.fn().mockResolvedValue(false),
    create: jest.fn((value: Partial<Company>) => Object.assign(new Company(), value)),
  };
  const refreshSessions = {
    create: jest.fn((value: Partial<RefreshSession>) => Object.assign(new RefreshSession(), value)),
    save: jest.fn(async (value: RefreshSession) => value),
  };
  const jwt = { signAsync: jest.fn().mockResolvedValue('signed-access-token') };
  const emailNotifier = {
    sendPasswordReset: jest.fn().mockResolvedValue(undefined),
    sendEmailChange: jest.fn().mockResolvedValue(undefined),
  };

  const service = new AuthService(
    users as unknown as Repository<User>,
    companies as unknown as Repository<Company>,
    refreshSessions as unknown as Repository<RefreshSession>,
    dataSource as unknown as DataSource,
    jwt as unknown as JwtService,
    emailNotifier,
  );
  return {
    service,
    users,
    companies,
    refreshSessions,
    dataSource,
    manager,
    queryBuilder,
    jwt,
    emailNotifier,
  };
}

describe('AuthService', () => {
  it('UT-AUTH-01 registra un student y emite tokens', async () => {
    const { service, users, refreshSessions, jwt } = createService();
    const result = await service.register({
      email: '  Persona@Ejemplo.com ',
      password: 'secure-password-123',
      role: UserRole.STUDENT,
    });

    expect(users.create).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'persona@ejemplo.com', role: UserRole.STUDENT }),
    );
    expect(result.user.role).toBe(UserRole.STUDENT);
    expect(result.access_token).toBe('signed-access-token');
    expect(result.refresh_token).toBeTruthy();
    expect(refreshSessions.save).toHaveBeenCalled();
    expect(jwt.signAsync).toHaveBeenCalledWith(
      { sub: 'user-1', role: UserRole.STUDENT },
      expect.objectContaining({ header: expect.objectContaining({ alg: 'RS256' }) }),
    );
  });

  it('UT-AUTH-02 crea empresa solo con CUIT válido', async () => {
    const { service, companies } = createService();
    const result = await service.register({
      email: 'empresa@ejemplo.com',
      password: 'secure-password-123',
      role: UserRole.COMPANY,
      company: {
        legal_name: 'Empresa Ejemplo',
        cuit: '20329642330',
        activity: 'Tecnología',
      },
    });

    expect(result.user.company).toEqual({
      legal_name: 'Empresa Ejemplo',
      cuit: '20329642330',
      activity: 'Tecnología',
    });
    expect(companies.create).toHaveBeenCalled();
  });

  it('rechaza el registro de empresa cuando el CUIT no pasa el dígito verificador', async () => {
    const { service, dataSource } = createService();
    await expect(
      service.register({
        email: 'empresa@ejemplo.com',
        password: 'secure-password-123',
        role: UserRole.COMPANY,
        company: {
          legal_name: 'Empresa Ejemplo',
          cuit: '20329642331',
          activity: 'Tecnología',
        },
      }),
    ).rejects.toMatchObject({ status: 400 });
    expect(dataSource.transaction).not.toHaveBeenCalled();
  });

  it('UT-AUTH-03 rechaza credenciales inválidas con respuesta genérica', async () => {
    const { service, users } = createService();
    const passwordHash = await argon2.hash('correct-password-123');
    users.createQueryBuilder().getOne.mockResolvedValue(
      Object.assign(new User(), {
        id: 'user-1',
        email: 'persona@ejemplo.com',
        passwordHash,
        role: UserRole.STUDENT,
      }),
    );

    await expect(
      service.login({ email: 'persona@ejemplo.com', password: 'incorrect-password' }),
    ).rejects.toMatchObject({ status: 401, message: 'Email o contraseña incorrectos' });
  });

  it('UT-AUTH-04 devuelve el mismo mensaje de reset para emails inexistentes', async () => {
    const { service, users, emailNotifier } = createService();
    users.findOne.mockResolvedValue(null);

    const response = await service.requestPasswordReset({ email: 'nadie@ejemplo.com' });

    expect(response.message).toContain('Si el email está registrado');
    expect(emailNotifier.sendPasswordReset).not.toHaveBeenCalled();
  });

  it('UT-AUTH-05 consume un reset y revoca las sesiones anteriores', async () => {
    const { service, manager, queryBuilder } = createService();
    const rawToken = 'a'.repeat(43);
    manager.findOne.mockResolvedValue(
      Object.assign(new ActionToken(), {
        id: 'action-1',
        userId: 'user-1',
        purpose: ActionTokenPurpose.PASSWORD_RESET,
      }),
    );

    await service.confirmPasswordReset({
      token: rawToken,
      new_password: 'a-new-secure-password',
    });

    expect(manager.update).toHaveBeenCalledWith(
      ActionToken,
      expect.objectContaining({ id: 'action-1' }),
      expect.objectContaining({ consumedAt: expect.any(Date) }),
    );
    expect(queryBuilder.update).toHaveBeenCalledWith(RefreshSession);
    expect(queryBuilder.execute).toHaveBeenCalled();
  });

  it('UT-AUTH-06 rechaza refresh tokens no registrados', async () => {
    const { service, manager } = createService();
    manager.findOne.mockResolvedValue(null);

    await expect(service.refresh('x'.repeat(64))).rejects.toMatchObject({ status: 401 });
  });

  it('al cambiar contraseña invalida sesiones refresh activas', async () => {
    const { service, users, manager, queryBuilder } = createService();
    const currentPasswordHash = await argon2.hash('current-password-123');
    queryBuilder.getOne.mockResolvedValue(
      Object.assign(new User(), {
        id: 'user-1',
        email: 'persona@ejemplo.com',
        passwordHash: currentPasswordHash,
        role: UserRole.STUDENT,
      }),
    );

    await service.changePassword('user-1', {
      current_password: 'current-password-123',
      new_password: 'new-secure-password-456',
    });

    expect(manager.update).toHaveBeenCalledWith(
      User,
      'user-1',
      expect.objectContaining({ passwordHash: expect.any(String) }),
    );
    expect(queryBuilder.update).toHaveBeenCalledWith(RefreshSession);
    expect(queryBuilder.execute).toHaveBeenCalled();
    expect(users.createQueryBuilder).toHaveBeenCalled();
  });

  it('UT-AUTH-07 publica la clave RSA pública como JWKS', async () => {
    const previousPath = process.env.JWT_PUBLIC_KEY_PATH;
    const directory = mkdtempSync(join(tmpdir(), 'auth-jwks-'));
    try {
      const { publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
      const publicKeyPath = join(directory, 'public.pem');
      writeFileSync(publicKeyPath, publicKey.export({ type: 'spki', format: 'pem' }));
      process.env.JWT_PUBLIC_KEY_PATH = publicKeyPath;

      const { service } = createService();
      const jwks = await service.getJwks();

      expect(jwks.keys).toHaveLength(1);
      expect(jwks.keys[0]).toMatchObject({ kty: 'RSA', alg: 'RS256', use: 'sig' });
      expect(jwks.keys[0].n).toBeTruthy();
      expect(jwks.keys[0].e).toBeTruthy();
    } finally {
      if (previousPath === undefined) {
        delete process.env.JWT_PUBLIC_KEY_PATH;
      } else {
        process.env.JWT_PUBLIC_KEY_PATH = previousPath;
      }
      rmSync(directory, { recursive: true, force: true });
    }
  });
});
