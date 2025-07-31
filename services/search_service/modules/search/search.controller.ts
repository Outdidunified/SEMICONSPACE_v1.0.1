
import { Controller, Get, Query } from '@nestjs/common';
import { SearchService } from './search.service';

@Controller('search')
export class SearchController {
  constructor(private readonly searchService: SearchService) {}

  @Get()
  async search(@Query('q') q: string) {
    if (!q || q.trim().length === 0) {
      return { count: 0, hits: [], message: 'Empty query not allowed' };
    }
    return this.searchService.search(q);
  }
}
