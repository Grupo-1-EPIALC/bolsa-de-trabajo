import { Transform, Type } from 'class-transformer';
import {
  IsBoolean,
  IsEmail,
  IsIn,
  IsInt,
  IsOptional,
  IsString,
  Length,
  Matches,
  Max,
  MaxLength,
  Min,
  ValidateNested,
} from 'class-validator';
import { UserRole } from '../users/user-role';

const toBoolean = ({ value }: { value: unknown }) =>
  value === true || value === 'true' || value === '1';

export class ListUsersQuery {
  @IsOptional()
  @IsIn(Object.values(UserRole))
  role?: UserRole;

  /** Busca en email, razón social y CUIT. */
  @IsOptional()
  @IsString()
  @MaxLength(120)
  q?: string;

  /** Incluye las cuentas borradas (auditoría). Por defecto no se listan. */
  @IsOptional()
  @Transform(toBoolean)
  @IsBoolean()
  include_deleted?: boolean;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  page = 1;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  size = 20;
}

export class AdminCompanyUpdateDto {
  @IsOptional()
  @IsString()
  @Length(1, 200)
  legal_name?: string;

  @IsOptional()
  @IsString()
  @Matches(/^\d{11}$/)
  cuit?: string;

  @IsOptional()
  @IsString()
  @Length(1, 160)
  activity?: string;
}

export class AdminUpdateUserDto {
  /** Cambio directo de email (sin confirmación): lo hace el admin. */
  @IsOptional()
  @IsEmail()
  @MaxLength(320)
  email?: string;

  @IsOptional()
  @ValidateNested()
  @Type(() => AdminCompanyUpdateDto)
  company?: AdminCompanyUpdateDto;
}
