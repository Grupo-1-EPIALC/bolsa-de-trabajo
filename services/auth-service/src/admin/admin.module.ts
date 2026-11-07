import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';
import { AuthModule } from '../auth/auth.module';
import { RolesGuard } from '../auth/roles.guard';
import { User } from '../users/user.entity';
import {
  ACCOUNT_EVENT_DELIVERY_STORE,
  ACCOUNT_EVENT_OUTBOX,
  ACCOUNT_EVENT_SENDER,
  AccountEventSender,
  DeliveryStore,
} from './account-events';
import { AccountEventDispatcher, dispatcherOptionsFromEnv } from './account-event-dispatcher';
import { AdminUsersController } from './admin-users.controller';
import { AdminUsersService } from './admin-users.service';
import { HttpAccountEventSender, subscribersFromEnv } from './http-account-event-sender';
import { TypeOrmAccountEventOutbox, TypeOrmDeliveryStore } from './typeorm-account-event-outbox';

@Module({
  imports: [TypeOrmModule.forFeature([User]), AuthModule],
  controllers: [AdminUsersController],
  providers: [
    AdminUsersService,
    RolesGuard,
    { provide: ACCOUNT_EVENT_SENDER, useFactory: () => new HttpAccountEventSender() },
    {
      provide: ACCOUNT_EVENT_DELIVERY_STORE,
      useFactory: (dataSource: DataSource) => new TypeOrmDeliveryStore(dataSource),
      inject: [DataSource],
    },
    {
      provide: AccountEventDispatcher,
      useFactory: (store: DeliveryStore, sender: AccountEventSender) =>
        new AccountEventDispatcher(store, sender, dispatcherOptionsFromEnv()),
      inject: [ACCOUNT_EVENT_DELIVERY_STORE, ACCOUNT_EVENT_SENDER],
    },
    {
      provide: ACCOUNT_EVENT_OUTBOX,
      useFactory: (dispatcher: AccountEventDispatcher) =>
        new TypeOrmAccountEventOutbox(subscribersFromEnv(), () => dispatcher.trigger()),
      inject: [AccountEventDispatcher],
    },
  ],
})
export class AdminModule {}
