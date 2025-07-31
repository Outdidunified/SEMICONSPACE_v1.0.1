import { Injectable, Logger } from '@nestjs/common';
import { typesenseClient } from './typesense.client';

@Injectable()
export class SearchService {
  private readonly logger = new Logger(SearchService.name);

  /**
   * Create or update a product document in Typesense
   */
  async createOrUpdateProduct(product: any) {
    try {
      if (!product || !product.id) {
        this.logger.warn('⚠️ Skipping indexing: Product or ID missing');
        return;
      }

      await typesenseClient
        .collections('products')
        .documents()
        .upsert(product);

      this.logger.log(`✅ Product upserted to Typesense: ${product.name || product.id}`);
    } catch (err) {
      this.logger.error('❌ Typesense indexing error:', err.message);
    }
  }

  /**
   * Search for products by query, filtering only active ones (status: true)
   */
  async search(query: string) {
    try {
      const searchParams = {
        q: query,
        query_by: 'name,description,supplier,manufacturer_part_number,category',
        filter_by: 'status:=true', // 🔐 Only return active products
        prefix: true,              // 🔁 Enables autocomplete-like search
        typo_tokens_threshold: 100, // 🔤 Typo tolerance for long queries
        num_typos: 2,              // 🔤 Allow up to 2 typos
        sort_by: '_text_match:desc', // 🔼 Best match first
        per_page: 20,
        exhaustive_search: false,   // ⚡️ Faster partial results
      };

      const result = await typesenseClient
        .collections('products')
        .documents()
        .search(searchParams);

      return {
        count: result.found,
        hits: result.hits.map((hit) => hit.document),
      };
    } catch (err) {
      this.logger.error('❌ Typesense search failed:', err.message);
      return { count: 0, hits: [] };
    }
  }
}