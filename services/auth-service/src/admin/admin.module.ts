import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AuthModule } from '../auth/auth.module';
import { RolesGuard } from '../auth/roles.guard';
import { User } from '../users/user.entity';
import { ACCOUNT_EVENT_PUBLISHER } from './account-events';
import { AdminUsersController } from './admin-users.controller';
import { AdminUsersService } from './admin-users.service';
import { HttpAccountEventPublisher } from './http-account-event-publisher';

@Module({
  imports: [TypeOrmModule.forFeature([User]), AuthModule],
  controllers: [AdminUsersController],
  providers: [
    AdminUsersService,
    RolesGuard,
    { provide: ACCOUNT_EVENT_PUBLISHER, useFactory: () => new HttpAccountEventPublisher() },
  ],
})
export class AdminModule {}
