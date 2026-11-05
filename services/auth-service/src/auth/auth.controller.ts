import { Body, Controller, Get, HttpCode, HttpStatus, Post, UseGuards } from '@nestjs/common';
import { AuthService } from './auth.service';
import {
  ChangeEmailDto,
  ChangePasswordDto,
  EmailConfirmDto,
  LoginDto,
  PasswordResetConfirmDto,
  PasswordResetRequestDto,
  RefreshTokenDto,
  RegisterDto,
} from './auth.dto';
import { CurrentUser, AuthenticatedUser } from './current-user.decorator';
import { JwtAuthGuard } from './jwt-auth.guard';

@Controller()
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Post('register')
  register(@Body() request: RegisterDto) {
    return this.authService.register(request);
  }

  @Post(['login', 'token'])
  @HttpCode(HttpStatus.OK)
  login(@Body() request: LoginDto) {
    return this.authService.login(request);
  }

  @Post('token/refresh')
  @HttpCode(HttpStatus.OK)
  refresh(@Body() request: RefreshTokenDto) {
    return this.authService.refresh(request.refresh_token);
  }

  @Get('me')
  @UseGuards(JwtAuthGuard)
  getProfile(@CurrentUser() user: AuthenticatedUser) {
    return this.authService.getProfile(user.sub);
  }

  @Post('password/change')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard)
  changePassword(@CurrentUser() user: AuthenticatedUser, @Body() request: ChangePasswordDto) {
    return this.authService.changePassword(user.sub, request);
  }

  @Post('password/reset')
  @HttpCode(HttpStatus.OK)
  requestPasswordReset(@Body() request: PasswordResetRequestDto) {
    return this.authService.requestPasswordReset(request);
  }

  @Post('password/reset/confirm')
  @HttpCode(HttpStatus.OK)
  confirmPasswordReset(@Body() request: PasswordResetConfirmDto) {
    return this.authService.confirmPasswordReset(request);
  }

  @Post('email/change')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard)
  requestEmailChange(@CurrentUser() user: AuthenticatedUser, @Body() request: ChangeEmailDto) {
    return this.authService.requestEmailChange(user.sub, request);
  }

  @Post('email/confirm')
  @HttpCode(HttpStatus.OK)
  confirmEmailChange(@Body() request: EmailConfirmDto) {
    return this.authService.confirmEmailChange(request.token);
  }

  @Get('.well-known/jwks.json')
  getJwks() {
    return this.authService.getJwks();
  }
}
