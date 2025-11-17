/**
 * Household-Meter Assignments API Route
 *
 * Manages the many-to-many relationship between households and meters
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export const dynamic = 'force-dynamic';

/**
 * GET /api/config/household-meters?household_id=xxx
 * Get all meter assignments for a household
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const householdId = searchParams.get('household_id');

    if (!householdId) {
      return NextResponse.json(
        { error: 'household_id is required' },
        { status: 400 }
      );
    }

    const assignments = await prisma.householdMeter.findMany({
      where: { householdId },
      include: {
        meter: true,
        household: true,
      },
    });

    return NextResponse.json({ assignments });
  } catch (error) {
    console.error('Failed to fetch household-meter assignments:', error);
    return NextResponse.json(
      { error: 'Failed to fetch assignments' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/config/household-meters
 * Assign a meter to a household
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();

    const {
      householdId,
      meterId,
      allocationType = 'direct',
      allocationValue = 100,
    } = body;

    // Validate required fields
    if (!householdId || !meterId) {
      return NextResponse.json(
        { error: 'Missing required fields: householdId, meterId' },
        { status: 400 }
      );
    }

    const assignment = await prisma.householdMeter.create({
      data: {
        householdId,
        meterId,
        allocationType,
        allocationValue,
      },
      include: {
        meter: true,
        household: true,
      },
    });

    return NextResponse.json({ assignment }, { status: 201 });
  } catch (error: any) {
    console.error('Failed to create household-meter assignment:', error);

    if (error.code === 'P2002') {
      return NextResponse.json(
        { error: 'This meter is already assigned to this household' },
        { status: 409 }
      );
    }

    if (error.code === 'P2003') {
      return NextResponse.json(
        { error: 'Household or meter not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to create assignment' },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/config/household-meters?id=assignment_id
 * Update meter assignment allocation
 */
export async function PATCH(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const assignmentId = searchParams.get('id');

    if (!assignmentId) {
      return NextResponse.json(
        { error: 'Assignment ID is required' },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { allocationType, allocationValue } = body;

    const assignment = await prisma.householdMeter.update({
      where: { id: parseInt(assignmentId) },
      data: {
        allocationType,
        allocationValue,
      },
      include: {
        meter: true,
        household: true,
      },
    });

    return NextResponse.json({ assignment });
  } catch (error: any) {
    console.error('Failed to update household-meter assignment:', error);

    if (error.code === 'P2025') {
      return NextResponse.json(
        { error: 'Assignment not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to update assignment' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/config/household-meters?id=assignment_id
 * Remove a meter from a household
 */
export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const assignmentId = searchParams.get('id');

    if (!assignmentId) {
      return NextResponse.json(
        { error: 'Assignment ID is required' },
        { status: 400 }
      );
    }

    await prisma.householdMeter.delete({
      where: { id: parseInt(assignmentId) },
    });

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error('Failed to delete household-meter assignment:', error);

    if (error.code === 'P2025') {
      return NextResponse.json(
        { error: 'Assignment not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to delete assignment' },
      { status: 500 }
    );
  }
}
