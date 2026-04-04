# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0](https://github.com/jayzerg/eduplan-ph/compare/v1.0.0...v1.1.0) (2026-04-04)


### Features

* Add AI topic suggestions feature ([ec14ee6](https://github.com/jayzerg/eduplan-ph/commit/ec14ee6b9b01cd3f3086d146bd063be63513d7f4))
* Add AI-powered topic suggestions ([0eb7a44](https://github.com/jayzerg/eduplan-ph/commit/0eb7a44875914701035a76cd9599a0df9d59e798))
* add inline code markdown support and html escaping to _md_inline function ([2496746](https://github.com/jayzerg/eduplan-ph/commit/24967469fc7758a6a8ee896f056d752c77571e74))
* add local configuration for OpenRouter API integration ([079a6a0](https://github.com/jayzerg/eduplan-ph/commit/079a6a059ea7b8f8c31bbb276b7081a40519f4d3))
* add MATATAG curriculum support and modularize codebase into src directory ([34157a1](https://github.com/jayzerg/eduplan-ph/commit/34157a180a6730d7636d05bded6116ea3f9f5e2e))
* centralize configuration in src/config.py and implement automated release workflows ([0aaa790](https://github.com/jayzerg/eduplan-ph/commit/0aaa790b7d47ffff14c281d5917732c630454e9f))
* implement academic aesthetic theme and update UI styling with custom CSS and configuration ([40082f0](https://github.com/jayzerg/eduplan-ph/commit/40082f09c262c1b23d37b62c49231a0021b161e2))
* implement AI generation logic and SQLite-based caching system for lesson plans ([f838fa5](https://github.com/jayzerg/eduplan-ph/commit/f838fa5700ce3d5c33659d61c6c4fd94a4541792))
* implement AI generation logic with OpenRouter integration, retry mechanisms, and content validation ([7aea8f5](https://github.com/jayzerg/eduplan-ph/commit/7aea8f5d266d12b5442e5ca1142ad7271e7a1861))
* implement AI-driven lesson plan generation with DepEd curriculum alignment and caching support ([866b8f4](https://github.com/jayzerg/eduplan-ph/commit/866b8f49e94138bade9fe6062e2b2b7fe1bff24c))
* implement threaded progress bar for long-running lesson plan generation tasks ([43f7e6c](https://github.com/jayzerg/eduplan-ph/commit/43f7e6c736c6a1802a2c622e86307d1edb3c163d))


### Bug Fixes

* completely decouple topic widget state from input value variable ([c962fec](https://github.com/jayzerg/eduplan-ph/commit/c962fecdb31332c80d28a9fe1df37ade20d07e53))
* decouple topic widget key to resolve StreamlitAPIException ([4aed722](https://github.com/jayzerg/eduplan-ph/commit/4aed72273094e591508060ca5e6ca2ddfeb6999b))
* rename .release-please-config.json to release-please-config.json ([527c448](https://github.com/jayzerg/eduplan-ph/commit/527c4486be8a717c0f8267919d0dc9f7b8348afa))
* resolve StreamlitAPIException on topic suggestion click ([beb8bdd](https://github.com/jayzerg/eduplan-ph/commit/beb8bdd44683d33f0582e090b298b1d07941f0e2))

## [1.0.0] - 2024-01-01

### Added
- Initial release of EduPlan PH
- DepEd-aligned lesson plan generation (6-section DLP format)
- Support for English, Filipino, and Taglish output
- Quiz extraction and CSV export
- DOCX and PDF export for lesson plans
- Multiple AI model support (Llama 3 70B, 8B, Mixtral)
- Input validation and error handling
- Unit tests for generator and utils modules
- Deployment documentation for Streamlit Cloud
