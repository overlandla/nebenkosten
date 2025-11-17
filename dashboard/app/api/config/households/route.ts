/**
 * Households API Route
 *
 * Provides CRUD operations for household management
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import type { Prisma } from '@prisma/client';

export const dynamic = 'force-dynamic';

/**
 * GET /api/config/households
 * Get all households with their assigned meters
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const activeOnly = searchParams.get('active') !== 'false';

    const where: Prisma.HouseholdWhereInput = {};

    if (activeOnly) {
      where.active = true;
    }

    const households = await prisma.household.findMany({
      where,
      orderBy: { id: 'asc' },
      include: {
        householdMeters: {
          include: {
            meter: {
              select: {
                id: true,
                name: true,
                meterType: true,
                unit: true,
                active: true,
              },
            },
          },
        },
      },
    });

    return NextResponse.json({ households });
  } catch (error) {
    console.error('Failed to fetch households:', error);
    return NextResponse.json(
      { error: 'Failed to fetch households' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/config/households
 * Create a new household
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();

    const {
      id,
      name,
      floors = [],
      allocationPercentage,
      active = true,
    } = body;

    // Validate required fields
    if (!id || !name) {
      return NextResponse.json(
        { error: 'Missing required fields: id, name' },
        { status: 400 }
      );
    }

    const household = await prisma.household.create({
      data: {
        id,
        name,
        floors,
        allocationPercentage: allocationPercentage || null,
        active,
      },
    });

    return NextResponse.json({ household }, { status: 201 });
  } catch (error: any) {
    console.error('Failed to create household:', error);

    if (error.code === 'P2002') {
      return NextResponse.json(
        { error: 'Household ID already exists' },
        { status: 409 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to create household' },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/config/households?id=household_id
 * Update an existing household
 */
export async function PATCH(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const householdId = searchParams.get('id');

    if (!householdId) {
      return NextResponse.json(
        { error: 'Household ID is required' },
        { status: 400 }
      );
    }

    const body = await request.json();

    const updateData: Prisma.HouseholdUpdateInput = {};

    if (body.name !== undefined) updateData.name = body.name;
    if (body.floors !== undefined) updateData.floors = body.floors;
    if (body.allocationPercentage !== undefined) {
      updateData.allocationPercentage = body.allocationPercentage;
    }
    if (body.active !== undefined) updateData.active = body.active;

    const household = await prisma.household.update({
      where: { id: householdId },
      data: updateData,
    });

    return NextResponse.json({ household });
  } catch (error: any) {
    console.error('Failed to update household:', error);

    if (error.code === 'P2025') {
      return NextResponse.json(
        { error: 'Household not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to update household' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/config/households?id=household_id
 * Delete a household
 */
export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const householdId = searchParams.get('id');

    if (!householdId) {
      return NextResponse.json(
        { error: 'Household ID is required' },
        { status: 400 }
      );
    }

    await prisma.household.delete({
      where: { id: householdId },
    });

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error('Failed to delete household:', error);

    if (error.code === 'P2025') {
      return NextResponse.json(
        { error: 'Household not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to delete household' },
      { status: 500 }
    );
  }
}
