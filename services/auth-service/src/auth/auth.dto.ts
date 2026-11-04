import { Type } from 'class-transformer';
import {
  IsDefined,
  IsEmail,
  IsIn,
  IsString,
  Length,
  Matches,
  MaxLength,
  MinLength,
  ValidateIf,
  ValidateNested,
} from 'class-validator';
import { UserRole } from '../users/user-role';

export class CompanyRegistrationDto {
  @IsString()
  @Length(1, 200)
  legal_name!: string;

  @IsString()
  @Matches(/^\d{11}$/)
  cuit!: string;

  @IsString()
  @Length(1, 160)
  activity!: string;
}

export class RegisterDto {
  @IsEmail()
  @MaxLength(320)
  email!: string;

  @IsString()
  @MinLength(12)
  @MaxLength(128)
  password!: string;

  @IsIn([UserRole.STUDENT, UserRole.COMPANY])
  role!: UserRole.STUDENT | UserRole.COMPANY;

  @ValidateIf((request: RegisterDto) => request.role === UserRole.COMPANY)
  @IsDefined()
  @ValidateNested()
  @Type(() => CompanyRegistrationDto)
  company?: CompanyRegistrationDto;
}

export class LoginDto {
  @IsEmail()
  @MaxLength(320)
  email!: string;

  @IsString()
  @MinLength(1)
  @MaxLength(128)
  password!: string;
}

export class RefreshTokenDto {
  @IsString()
  @MinLength(32)
  @MaxLength(256)
  refresh_token!: string;
}

export class ChangePasswordDto {
  @IsString()
  @MinLength(1)
  @MaxLength(128)
  current_password!: string;

  @IsString()
  @MinLength(12)
  @MaxLength(128)
  new_password!: string;
}

export class PasswordResetRequestDto {
  @IsEmail()
  @MaxLength(320)
  email!: string;
}

export class PasswordResetConfirmDto {
  @IsString()
  @MinLength(32)
  @MaxLength(256)
  token!: string;

  @IsString()
  @MinLength(12)
  @MaxLength(128)
  new_password!: string;
}

export class ChangeEmailDto {
  @IsEmail()
  @MaxLength(320)
  email!: string;

  @IsString()
  @MinLength(1)
  @MaxLength(128)
  current_password!: string;
}

export class EmailConfirmDto {
  @IsString()
  @MinLength(32)
  @MaxLength(256)
  token!: string;
}
